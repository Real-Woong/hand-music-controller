# MediaPipe로 손 랜드마크 추출
import cv2
import mediapipe as mp

class HandData:
    def __init__(self, landmarks, handedness, frame_width, frame_height):
        """
        constructor
        landmarks: (x, y, z)mediapipe Hand 모델이 손에서 춫ㄹ하는 21개의 고정된 관절 좌표 리스트
                   list안에는 tuple 로 존제 [(123.4, 200.1, -0.02), (130.2, 180.7, -0.01),]
        handedness: 'Left' or 'Right'
        """
        self.landmarks = landmarks
        self.handedness = handedness
        self.frame_width = frame_width
        self.frame_height = frame_height

    def center(self):
        """ 손목(0)과 중지 MCP(9) 중간 정도로 손 중심정 대충 계산 """
        wrist = self.landmarks[0]
        middle_mcp = self.landmarks[9]
        index_mcp = self.landmarks[5]
        pinky_mcp = self.landmarks[17]
        cx = (wrist[0] + middle_mcp[0] + index_mcp[0] + pinky_mcp[0]) / 4
        cy = (wrist[1] + middle_mcp[1] + index_mcp[1] + pinky_mcp[1]) / 4
        return cx, cy
    
class HandTracker:
    def __init__(self, max_num_hands = 1, detection_confidence = 0.5, tracking_confidence = 0.5):
        """constructor"""
        # Mediapipe의 hands 솔루션 모듈을 불러옴
        self.mp_hands = mp.solutions.hands

        # 실제 Hand Tracking 모델 생성 (손 추적기 준비)
        self.hands = self.mp_hands.Hands(
            static_image_mode = False, # 동영상 입력 (매 프레임 추적 모드)
            max_num_hands = max_num_hands, # 최대 몇 개 손을 찾을지
            min_detection_confidence = detection_confidence, # 손 처름 찾을 때 기준
            min_tracking_confidence = tracking_confidence, # 추적 유지 기준
        )

    def process(self, frame_bgr):
        """ BGR 프레임 → HandData 리스트 반환 """
        # frame.shape = (height, width, channels)
        h, w, _ = frame_bgr.shape # 프레임의 세로(h), 가로(w), 채널 수 가져오기

        # opcv는 brg순으로 읽지만, mp 는 rgb순으로 즉 변환 필요
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        # mp 손인식 모델에 전달 -> 손 랜드마크 분석
        results = self.hands.process(frame_rgb)

        hand_list = [] # return 리스트

        # 손이 감지된 경우에만 처리
        if results.multi_hand_landmarks and results.multi_handedness:
            #여러 손 지원 -> 랜드마크와 왼손/오른손 정보를 묶어서 반복 
            for lm, handedness in zip(results.multi_hand_landmarks, results.multi_handedness) :
                lm_list = [] # 21개의 랜드마크 좌표를 넣을 리스트
                for p in lm.landmark:
                    lm_list.append((p.x * w, p.y * h, p.z)) # 랜드마크 좌표 0~1 사이 값으로 -> 픽셀 좌표로 변환
                label = handedness.classification[0].label # 오른손 왼손 확인

                hand_list.append(HandData(lm_list, label, w, h)) # return 값에 넣기 (랜드마크 리스트, 왼손 오른손, 프레임 가로/세로)

        return hand_list # 만약 손이 없으면 빈 리스트 return

    def draw(self, frame_bgr, hand_list):
        """ 디버깅용 손 랜드마크 그리기 """

        # 프레임 크기 가져오기
        h, w, _ = frame_bgr.shape

        # mp 그리기 유틸 가져오기
        mp_drawing = mp.solutions.drawing_utils
        mp_style = mp.solutions.drawing_styles

        # hand_list 안에는 HandData 객체들이 들어있음 위에 process 참조
        for hand in hand_list:
            lm_list = hand.landmarks # 손의 21개 (x,y,z) 좌표 리스트

            # 각 랜드마크 점 찍기
            for (x, y, z) in lm_list:
                cv2.circle(frame_bgr, (int(x), int(y)), 4, (0, 255, 0), -1) #초록 점

            # Hand_Connections 정보를 이용해서 뼈대(선) 그리기
            for start_idx, end_idx in self.mp_hands.HAND_CONNECTIONS:
                x1, y1, _ = lm_list[start_idx]
                x2, y2, _ = lm_list[end_idx]
                cv2.line(
                    frame_bgr,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 255), # 노란 선
                    2
                )

            # 손 중심점도 별도로 표시
            cx, cy = hand.center()
            cv2.circle(frame_bgr, (int(cx), int(cy)), 8, (0, 0, 255), 2) #빨간 동그라미
        
        return frame_bgr



''' 개발자(진웅) 위한 브래인 스토밍
1. 객체 생성 → Mediapipe 손 모델 로딩
2. process() 호출
3. 이미지 크기(h, w) 추출
4. BGR → RGB 변환
5. Mediapipe로 손 분석
6. 손이 있으면:
   - 21개 랜드마크를 픽셀 좌표로 변환
   - 왼손/오른손 판단
   - HandData 객체로 묶어서 리스트에 저장
7. hand_list 반환
'''
        
