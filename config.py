# 임계값, 하이퍼파라미터 모음

#화면 크기 가정 (웹캠에서 읽어서 동적으로 잡아도 되지만 기본값)
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# 제스처 관련 임계값
SWIPE_MIN_DIST = 0.20 # x축 이동 (정규화 기준) 이만큼 넘으면 스와이프
VOLUME_VEL_SCALE = 0.8 # 세로 속도 -> 볼륨 변화량 스케일
VOLUME_MAX_STEP = 0.08 # 한 프레임에서 최대 볼륨 변화량

ROLL_2X_THRESHOLD = 15
ROLL_4X_THRESHOLD = 35

# 프레임 히스토리
HISTORY_LENGTH = 5 # 속도 계산용 최근 프레임 수

# DJ 모드가 아닌 상태에서도 화면에 표시는 할지 등등
SHOW_DEBUG_TEXT = True

# Music_Controller 기본 범위 볼륨
MIN_VOLUME = 0.0
MAX_VOLUME = 1.0
INITIAL_VOLUME = 0.5