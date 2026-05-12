import pygame
import os
import settings

class AudioManager:
    """Singleton quản lý âm thanh và nhạc nền cho game.

    Chỉ tồn tại một instance duy nhất — truy cập qua biến module audio_manager.
    Tự động disable nếu pygame.mixer không khởi tạo được.

    Attributes:
        enabled (bool): True nếu pygame.mixer hoạt động và audio được bật.
        sounds (dict): Map key → pygame.mixer.Sound đã tải.
        music_playing (str | None): Key nhạc nền đang phát, None nếu chưa phát.

    Usage::

        from systems.audio import audio_manager
        audio_manager.play_sound("tower_shoot")
        audio_manager.play_music("music_gameplay")
        audio_manager.stop_music()
    """
    _instance = None

    def __new__(cls):
        """Tạo hoặc trả về singleton instance của AudioManager.

        Returns:
            AudioManager: Instance duy nhất, tạo mới nếu chưa tồn tại.
        """
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Khởi tạo AudioManager: init mixer và load toàn bộ sounds từ settings.

        Side effects:
            - Gọi pygame.mixer.init() một lần duy nhất.
            - Gọi _load_sounds() để tải SFX từ settings.SOUNDS.
            - Nếu mixer lỗi: đặt enabled = False, audio bị vô hiệu hóa.
        """
        if self._initialized:
            return
        
        # Lấy giá trị từ settings, nếu không có thì mặc định True
        self.enabled = getattr(settings, 'AUDIO_ENABLED', True)
        self.sounds = {}
        self.music_playing = None
        
        try:
            pygame.mixer.init()
            self._load_sounds()
            self._initialized = True
            print("[AUDIO] System initialized.")
        except Exception as e:
            print(f"[AUDIO] Failed to initialize mixer: {e}")
            self.enabled = False

    def _load_sounds(self):
        """Tải tất cả sound effects vào memory."""
        # Lấy đường dẫn từ settings, mặc định data/audio
        audio_path = getattr(settings, 'AUDIO_PATH', 'data/audio')
        sounds_dict = getattr(settings, 'SOUNDS', {})
        
        for key, filename in sounds_dict.items():
            # Nhạc nền được xử lý riêng (streamed)
            if key.startswith("music_"):
                continue
                
            path = os.path.join(audio_path, filename)
            if os.path.exists(path):
                try:
                    self.sounds[key] = pygame.mixer.Sound(path)
                    # Lấy volume từ settings, mặc định 0.7
                    vol = getattr(settings, 'VOLUME_SFX', 0.7)
                    self.sounds[key].set_volume(vol)
                    print(f"[AUDIO] Loaded sound: {key}")
                except Exception as e:
                    print(f"[AUDIO] Error loading {filename}: {e}")
            else:
                print(f"[AUDIO] Sound file not found: {path}")

    def play_sound(self, key):
        """Phát một sound effect theo key.

        Args:
            key (str): Key của sound trong self.sounds (khớp với settings.SOUNDS).

        Side effects:
            - Gọi pygame.mixer.Sound.play() nếu enabled và key tồn tại.
            - Không làm gì nếu audio bị disable hoặc key không tìm thấy.
        """
        if not self.enabled or key not in self.sounds:
            return
        self.sounds[key].play()

    def play_music(self, key, loops=-1):
        """Phát nhạc nền (ogg/mp3) theo key; bỏ qua nếu đang phát cùng track.

        Args:
            key (str): Key nhạc nền trong settings.SOUNDS (phải bắt đầu bằng "music_").
            loops (int): Số lần lặp (-1 = vô hạn). Mặc định -1.

        Side effects:
            - Load và phát file nhạc qua pygame.mixer.music.
            - Cập nhật self.music_playing = key khi phát thành công.
            - Không làm gì nếu audio disable hoặc đang phát cùng key.
        """
        if not self.enabled:
            return

        if self.music_playing == key:
            return

        sounds_dict = getattr(settings, 'SOUNDS', {})
        filename = sounds_dict.get(key)
        if not filename:
            return

        audio_path = getattr(settings, 'AUDIO_PATH', 'data/audio')
        path = os.path.join(audio_path, filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                # Lấy volume từ settings, mặc định 0.5
                vol = getattr(settings, 'VOLUME_MUSIC', 0.5)
                pygame.mixer.music.set_volume(vol)
                pygame.mixer.music.play(loops)
                self.music_playing = key
                print(f"[AUDIO] Playing music: {key}")
            except Exception as e:
                print(f"[AUDIO] Error playing music {filename}: {e}")
        else:
            print(f"[AUDIO] Music file not found: {path}")

    def stop_music(self):
        """Dừng nhạc nền đang phát và reset trạng thái.

        Side effects:
            - Gọi pygame.mixer.music.stop() nếu audio enabled.
            - Đặt self.music_playing = None.
        """
        if self.enabled:
            pygame.mixer.music.stop()
            self.music_playing = None

# Singleton instance
audio_manager = AudioManager()
