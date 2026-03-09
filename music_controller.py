# 볼륨/재생/트랙 이동 제어
from config import MAX_VOLUME, MIN_VOLUME, INITIAL_VOLUME
import os
import vlc
from typing import Union, Sequence


class MusicController:

    def __init__(self, media_path: Union[str, Sequence[str]]):
        """
        media_path:
        - 문자열 하나: "music/my_song.mp3"
        - 또는 문자열 리스트: ["music/my_music1.mp3", "music/my_music2.mp3", ...]
        """

        # 1) 문자열이면 리스트로 감싸기
        if isinstance(media_path, str):
            media_path = [media_path]

        # 2) 실제 존재하는 파일만 필터링
        valid_paths = [p for p in media_path if os.path.exists(p)]
        if not valid_paths:
            raise FileNotFoundError(f"Media file not found: {media_path}")

        self.playlist = valid_paths
        self.current_index = 0

        # VLC 인스턴스 & 플레이어 생성
        self._vlc_instance = vlc.Instance()
        self._player = self._vlc_instance.media_player_new()

        # 상태 변수
        self.volume = INITIAL_VOLUME
        self.is_paused = False
        self.is_muted = False
        self.dj_mode = False  # V 사인으로 토글하는 DJ 모드

        self.playback_volume = self.volume

        # 현재 트랙 로드
        self._load_current_media()

        # 초기 볼륨 적용
        self._apply_volume()

    """============================== 트랙 헬퍼 =============================="""

    def _load_current_media(self, auto_play: bool = False):
        """
        현재 self.current_index에 해당하는 곡을 VLC에 로드
        """
        path = self.playlist[self.current_index]
        media = self._vlc_instance.media_new(path)
        self._player.set_media(media)

        # 볼륨 다시 적용
        self._apply_volume()

        if auto_play:
            self.play()

    """============================== 볼륨 적용 =============================="""

    def _apply_volume(self):
        """내부 VLC 볼륨에 현재 self.volume 반영 (0~100 스케일)"""
        # self.volume은 [MIN_VOLUME, MAX_VOLUME] 범위 안에서 관리한다고 가정
        norm = (self.volume - MIN_VOLUME) / (MAX_VOLUME - MIN_VOLUME)
        norm = max(0.0, min(1.0, norm))
        vlc_vol = int(norm * 100)
        self._player.audio_set_volume(vlc_vol)

    """============================== DJ Mode =============================="""

    def toggle_dj_mode(self):
        # 토글 전 상태 저장
        new_state = not self.dj_mode
        self.dj_mode = new_state

        if self.dj_mode:
            self.play()
        else:
            self.pause()

        print(f"[DJ MODE] {'ON' if self.dj_mode else 'OFF'}")

    """============================== 재생 제어 =============================="""

    def play(self):
        """처음 재생 / (필요하면) 다시 시작"""
        self._player.play()
        self.is_paused = False
        print("[MUSIC] Play")

    def pause(self) -> None:
        """일시정지 (이미 재생 중일 때만)"""
        if not self.is_paused:
            self._player.pause()
            self.is_paused = True
            print("[MUSIC] Pause")

    def resume(self) -> None:
        """일시정지 해제 (이미 일시정지 상태일 때만)"""
        if self.is_paused:
            self._player.play()
            self.is_paused = False
            print("[MUSIC] Resume")

    def toggle_play_pause(self):
        if self.is_paused:
            self.resume()
        else:
            self.pause()

    """============================== 볼륨 제어 =============================="""

    def change_volume(self, delta: float):
        """
        volume_delta (예: -0.02 ~ +0.02 정도)를 받아서
        MIN_VOLUME ~ MAX_VOLUME 범위 안에서 조정
        """
        self.volume += delta
        self.volume = max(MIN_VOLUME, min(MAX_VOLUME, self.volume))
        self._apply_volume()
        print(f"[MUSIC] Volume: {self.volume:.2f}")

    def mute(self):
        if not self.is_muted:
            self.is_muted = True
            self._backup_volume = self.volume
            self.volume = MIN_VOLUME
            self._apply_volume()
            print("[MUSIC] Mute (volume -> 0)")

    def unmute(self):
        if self.is_muted:
            self.is_muted = False
            if self._backup_volume < MIN_VOLUME:
                self._backup_volume = MIN_VOLUME
            self.volume = self._backup_volume
            self._apply_volume()
            print(f"[MUSIC] Unmute (volume -> {self.volume: .2f})")

    """============================== 트랙 이동 =============================="""

    def next_track(self):
        """다음 트랙으로 이동 후 자동 재생"""
        if len(self.playlist) <= 1:
            print("[MUSIC] Only one track in playlist")
            return
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self.is_paused = False
        self._load_current_media(auto_play=True)
        print(f"[MUSIC] Next track -> {self.playlist[self.current_index]}")

    def prev_track(self):
        """이전 트랙으로 이동 후 자동 재생"""
        if len(self.playlist) <= 1:
            print("[MUSIC] Only one track in playlist")
            return
        self.current_index = (self.current_index - 1) % len(self.playlist)
        self.is_paused = False
        self._load_current_media(auto_play=True)
        print(f"[MUSIC] Previous track -> {self.playlist[self.current_index]}")

    """============================== 좋아요 (지금은 로그만) =============================="""

    def like_current(self):
        print("[MUSIC] Like / Favorite this track")

    """============================== 상태 Debug =============================="""

    def get_status_text(self):
        status = []
        status.append(f"DJ: {'ON' if self.dj_mode else 'OFF'}")
        status.append(f"Paused: {self.is_paused}")
        status.append(f"Vol: {self.volume:.2f}")
        status.append(f"Muted: {self.is_muted}")
        status.append(f"Track: {self.current_index + 1}/{len(self.playlist)}")
        return " | ".join(status)
