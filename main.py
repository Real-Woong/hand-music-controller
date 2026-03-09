import cv2
import glob
import os

from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer, GestureType
from music_controller import MusicController

MUSIC_DIR = "./music"

def load_playlist():
    """
    ./music 폴더에서 my_music*.mp3 파일들을 찾아서 플레이리스트 생성
    """
    pattern = os.path.join(MUSIC_DIR, "my_music*.mp3")
    playlist = sorted(glob.glob(pattern))

    if not playlist:
        raise RuntimeError("music/ 폴더 안에 my_music*.mp3 파일이 하나도 없슴둥")
    
    return playlist

def main():
    # 카메라 인덱스는 환경에 따라 0 또는 1
    cap = cv2.VideoCapture(1)

    tracker = HandTracker(max_num_hands=1)
    recognizer = GestureRecognizer()

    # ./music/my_music1.mp3, my_music2.mp3 ... 자동으로 찾기
    playlist = load_playlist()
    controller = MusicController(playlist)

    # 처음부터 재생하고 싶으면 주석 해제
    # controller.play()

    v_was_down = False  # 직전 프레임에서 V 사인이었는지

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1) 손 추적
        hand_list = tracker.process(frame)

        # 2) 디버깅용: 랜드마크/뼈대/중심점 그리기
        frame = tracker.draw(frame, hand_list)

        debug_lines = []  # 이 프레임에서 화면에 띄울 텍스트들

        if hand_list:
            hand = hand_list[0]

            # (A) 현재 손 모양 (디버깅용)
            shape = recognizer.classify_hand_shape(hand)
            debug_lines.append(f"SHAPE: {shape}")

            # (B) 이 프레임에서 인식된 제스처 이벤트 전부
            events = recognizer.update(hand)

            # 쿨다운 디버그 정보
            cd = recognizer.get_cooldown_info(fps=30)
            debug_lines.append(
                f"COOLDOWN: {cd['frames_left']}f ≒ {cd['seconds_left']:.2f}s"
            )

            # 이번 프레임에 V 사인이 있었는지
            v_this_frame = any(ev.type == GestureType.V_SIGN for ev in events)

            # 콘솔 디버깅용
            # print([ (ev.type, ev.data) for ev in events ])

            for ev in events:
                # 어떤 이벤트들인지 화면에도 찍자 (디버깅)

                # 1) V 사인 -> DJ 모드 토글 (edge detect)
                if ev.type == GestureType.V_SIGN:
                    if not v_was_down:
                        controller.toggle_dj_mode()
                        debug_lines.append("EVENT: V_SIGN (toggle DJ)")
                    continue

                # 5) 볼륨 제스처
                elif ev.type == GestureType.VOLUME_MOVE:
                    delta = ev.data.get("volume_delta", 0.0)
                    controller.change_volume(delta)
                    debug_lines.append(f"EVENT: VOLUME_MOVE ({delta:+.3f})")
                        
                # DJ 모드 OFF면 나머지 제스처는 무시
                elif not controller.dj_mode:
                    continue

                # 2) 주먹/손바닥 -> 일시정지/재생
                elif ev.type == GestureType.FIST:
                    controller.pause()
                    debug_lines.append("EVENT: FIST (pause)")
                
                elif ev.type == GestureType.PALM:
                    controller.resume()
                    debug_lines.append("EVENT: PALM (resume)")

                # 4) '쉿' 제스처 (검지만 펴짐)/ 'OK 사인' (엄지 검지 오므려서 붙이기) -> Mute/Unmute
                elif ev.type == GestureType.INDEX_ONLY:
                    controller.mute()
                    debug_lines.append("EVENT: INDEX_ONLY (mute)")

                elif ev.type == GestureType.OK_SIGN:
                    controller.unmute()
                    debug_lines.append("EVENT: OK_SIGN (unmute)")

                # 6) 스와이프 → 트랙 이동
                elif ev.type == GestureType.SWIPE_RIGHT:
                    controller.next_track()
                    debug_lines.append("EVENT: SWIPE_RIGHT (next track)")

                elif ev.type == GestureType.SWIPE_LEFT:
                    controller.prev_track()
                    debug_lines.append("EVENT: SWIPE_LEFT (prev track)")

            # V 사인 edge-detect용 상태 업데이트
            v_was_down = v_this_frame

        else:
            # 손이 아예 화면에 없을 때
            debug_lines.append("NO HAND")

        # MusicController 상태도 같이 표시
        debug_lines.append(controller.get_status_text())

        # 4) 화면 왼쪽 위에 여러 줄로 디버그 텍스트 표시
        for i, text in enumerate(debug_lines):
            y = 30 + i * 30  # 줄마다 아래로 30px씩 내려가면서 출력
            cv2.putText(
                frame,
                text,
                (30, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        # 4) 화면 출력
        cv2.imshow("Hand DJ", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
