# gesture_recognizer.py
from enum import Enum, auto
from collections import deque
import math

from config import (
    SWIPE_MIN_DIST,        # 스와이프 판정에 필요한 최소 이동량
    VOLUME_MAX_STEP,       # 한 프레임에 허용할 최대 볼륨 변화량
    VOLUME_VEL_SCALE,      # 손 이동 속도를 볼륨 변화량으로 바꿀 때 곱해줄 배율
    HISTORY_LENGTH,        # 중심점 기록 몇 프레임까지 볼지
)


class GestureType(Enum):
    NONE = auto()
    V_SIGN = auto()
    FIST = auto()
    PALM = auto()
    INDEX_ONLY = auto()
    OK_SIGN = auto()
    SWIPE_LEFT = auto()
    SWIPE_RIGHT = auto()
    VOLUME_MOVE = auto()
    EVIL = auto()
    PINKY = auto()


class GestureEvent:
    def __init__(self, gtype, data=None):
        self.type = gtype
        self.data = data or {}


class GestureRecognizer:
    def __init__(self, cooldown_frames: int = 24):
        # 최근 중심점 기록 (볼륨 계산용, 스와이프용)
        self.center_history = deque(maxlen=HISTORY_LENGTH)

        # 제스처 쿨다운 (프레임 단위)
        self.cooldown_frames = cooldown_frames
        self.cooldown = 0

    """============================== 기본 유틸 =============================="""

    @staticmethod
    def _finger_is_extended(hand, tip_idx, pip_idx, margin: float = 7.0):
        """
        특정 손가락이 '펴졌는지' 여부 판단
        """
        lm = hand.landmarks
        tip_y = lm[tip_idx][1]
        pip_y = lm[pip_idx][1]
        return tip_y < pip_y - margin

    @staticmethod
    def _distance(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    """============================== 손 모양 분류 =============================="""

    def classify_hand_shape(self, hand):
        lm = hand.landmarks

        index_ext  = self._finger_is_extended(hand, 8,  6)
        middle_ext = self._finger_is_extended(hand, 12, 10)
        ring_ext   = self._finger_is_extended(hand, 16, 14)
        pinky_ext  = self._finger_is_extended(hand, 20, 18)

        fingers_ext = [index_ext, middle_ext, ring_ext, pinky_ext]
        ext_count = sum(fingers_ext)

        # 1) FIST: 네 손가락 하나도 안 펴졌으면 → 무조건 주먹
        if ext_count == 0:
            return "FIST"

        # 2) OK_SIGN (그대로 쓰고 싶으면 유지)
        thumb_tip = lm[4]
        index_tip = lm[8]
        index_pip = lm[6]
        circle_dist = self._distance(thumb_tip, index_tip)
        index_len   = self._distance(index_tip, index_pip) + 1e-6
        ratio = circle_dist / index_len
        extra_fingers_for_OK = sum([middle_ext, ring_ext, pinky_ext])

        if ratio < 0.6 and extra_fingers_for_OK == 3:
            return "OK_SIGN"

        # 3) VOLUME 전용 제스처: 🤘 (index + pinky만 펼친 상태)
        if index_ext and pinky_ext and not middle_ext and not ring_ext:
            return "EVIL"  # 이름은 그대로 쓰고 모양만 갈아끼움
        
        if pinky_ext and not index_ext and not middle_ext and not ring_ext:
            return "PINKY"
        
        # 4) V_SIGN: index + middle 만 펴져 있음
        if index_ext and middle_ext and not ring_ext and not pinky_ext:
            return "V_SIGN"

        # 5) INDEX_ONLY: 검지만 펴짐
        if index_ext and not middle_ext and not ring_ext and not pinky_ext:
            return "INDEX_ONLY"

        # 6) PALM: 3개 이상 펴져 있으면 손바닥
        if ext_count >= 3:
            return "PALM"

        return "OTHER"


    """============================== 메인 업데이트 =============================="""

    def update(self, hand):
        """
        한 손에 대해 현재 프레임에서 감지된 GestureEvent 목록 반환
        1) 손 모양 기반 제스처 (V 사인, 주먹, 손바닥 등)  -> shape_events
        2) 위치/속도 기반 (스와이프)                      -> motion_events
        3) 위치/속도 기반 (볼륨 조절)                      -> continuous_events
        """
        # 1) 손 모양 분류
        shape = self.classify_hand_shape(hand)

        shape_events = []       # FIST / PALM / V_SIGN / INDEX_ONLY / OK_SIGN
        motion_events = []      # SWIPE_LEFT / SWIPE_RIGHT
        continuous_events = []  # VOLUME_MOVE

        # --- 손 모양 기반(단발) 제스처들 ---
        if shape == "V_SIGN":
            shape_events.append(GestureEvent(GestureType.V_SIGN))

        if shape == "FIST":
            shape_events.append(GestureEvent(GestureType.FIST))

        if shape == "PALM":
            shape_events.append(GestureEvent(GestureType.PALM))

        if shape == "INDEX_ONLY":
            shape_events.append(GestureEvent(GestureType.INDEX_ONLY))

        if shape == "OK_SIGN":
            shape_events.append(GestureEvent(GestureType.OK_SIGN))

        # ⛔ EVIL 은 여기서 이벤트 안 만듦
        #    → 볼륨 상태로만 쓰고, 쿨다운에 영향 안 주게.

        # --- 위치/속도 기반 (스와이프 / 볼륨) ---
        cx, cy = hand.center()
        nx = cx / hand.frame_width
        ny = cy / hand.frame_height

        self.center_history.append((nx, ny))

        swiped = False  # 이번 프레임에서 스와이프가 이미 나갔는지 표시

        if len(self.center_history) >= HISTORY_LENGTH:
            prev_x, prev_y = self.center_history[0]
            dx = nx - prev_x
            dy = ny - prev_y

            # 2-1) 스와이프 (좌/우) -> motion_events
            if shape == "PINKY" and abs(dx) > SWIPE_MIN_DIST:
                if dx > 0:
                    motion_events.append(GestureEvent(GestureType.SWIPE_RIGHT))
                else:
                    motion_events.append(GestureEvent(GestureType.SWIPE_LEFT))
                swiped = True  # 🔹이 프레임에 이미 한 번 스와이프 발생

            # 2-2) 볼륨: "손날(EVIL)"일 때만 -> continuous_events
            #      + 스와이프랑 같은 프레임에서 같이 안 나오게
            if shape == "EVIL" and not swiped:
                volume_delta = -dy * VOLUME_VEL_SCALE
                volume_delta = max(-VOLUME_MAX_STEP, min(VOLUME_MAX_STEP, volume_delta))

                if abs(volume_delta) > 0.001:
                    continuous_events.append(
                        GestureEvent(
                            GestureType.VOLUME_MOVE,
                            data={"volume_delta": volume_delta}
                        )
                    )

            # 🔹스와이프가 한 번 발생했으면, 같은 제스처로 또 나가는 걸 막기 위해
            #    중심점 히스토리 리셋
            if swiped:
                self.center_history.clear()
                self.center_history.append((nx, ny))


        # --- 쿨다운 처리 ---
        if self.cooldown > 0:
            self.cooldown -= 1
            # 쿨다운 중에는 shape_events만 막고,
            # 스와이프 + 볼륨은 그대로 허용
            return motion_events + continuous_events

        # 쿨다운 아닐 때: 전부 허용
        events = shape_events + motion_events + continuous_events

        # 손 모양 단발 제스처가 하나라도 발생했다면 쿨다운 시작
        if shape_events:
            self.cooldown = self.cooldown_frames

        return events


    """============================== 디버그용 쿨다운 정보 =============================="""

    def get_cooldown_info(self, fps: float = 30.0):
        return {
            "frames_left": self.cooldown,
            "seconds_left": self.cooldown / fps
        }
