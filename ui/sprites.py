"""
ui/sprites.py — Load sprite từ file ảnh thực, fallback procedural nếu thiếu.
"""
import pygame
import os
import math
import settings

_cache: dict = {}
BASE = "data/sprites"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def init() -> None:
    """Pre-load toàn bộ sprites vào _cache. Phải gọi sau pygame.init() và display.set_mode().

    Side effects:
        - Lưu tất cả Surface/list[Surface] vào _cache với các key chuẩn.
        - Gọi _load_map_tiles() để load tile PATH/WALL từ ảnh thực.
        - Tạo procedural fallback cho mọi sprite thiếu file.

    Note:
        convert_alpha() yêu cầu display đã được khởi tạo.
        Các key cache: "tower_basic", "trojan_Run", "fireworm_Walk", "shadow_Walk", v.v.
    """
    cs       = settings.CELL_SIZE
    spr_size = int(cs * settings.SPRITE_SCALE)  # malware size
    twr_size = int(cs * settings.TOWER_SCALE)   # tower/server/portal — to và oai hơn
    blt_size = max(10, cs // 4)

    # --- Map tiles ---
    _load_map_tiles(cs)

    # --- Tower ---
    _cache["tower_basic"]  = _img(f"{BASE}/tower/BasicNode/Sniper Tower.png",       twr_size, twr_size)
    _cache["tower_ice"]    = _img(f"{BASE}/tower/IceWall/Base Spirit Tower.png",    twr_size, twr_size)
    _cache["tower_radar"]  = _img(f"{BASE}/tower/RadarNode/Posion Tower.png",       twr_size, twr_size)
    _cache["tower_speed"]  = _img(f"{BASE}/tower/SpeedNode/Charge Tower.png",       twr_size, twr_size)
    _cache["tower_fire"]   = _img(f"{BASE}/tower/FireNode/Flamethrower-Charge Tower.png", twr_size, twr_size)
    _cache["tower_sniper"] = _img(f"{BASE}/tower/SniperNode/Berserker Tower.png",   twr_size, twr_size)
    _cache["tower_freeze"] = _img(f"{BASE}/tower/FreezeNode/Basic Mage Tower.png",  twr_size, twr_size)
    _cache["tower_spread"] = _img(f"{BASE}/tower/SpreadNode/Alt. Necrosis Tower.png", twr_size, twr_size)
    _cache["tower_poison"] = _img(f"{BASE}/tower/PoisonNode/SoulSucker-Breaker.png", twr_size, twr_size)

    # --- Projectile ---
    _cache["proj_basic"] = _img(f"{BASE}/tower/BasicNode/Regular Bullet.png", blt_size, blt_size)
    _cache["proj_ice"]   = _img(f"{BASE}/tower/IceWall/Magic Bullet.png",     blt_size, blt_size)
    # Các tháp mới sử dụng custom draw functions với trail effect
    # (speed, sniper, freeze, spread, poison, fire được vẽ bằng hàm custom)

    # --- Portal spawn ---
    _cache["spawn"] = _sheet(f"{BASE}/portal/Portal_100x100px.png",
                              100, 100, max_frames=14, target=(twr_size, twr_size))

    # --- Server (4 frame pulse) ---
    base_srv = _img(f"{BASE}/server/Mage Tower.png", twr_size, twr_size)
    _cache["server"] = [_pulse_tint(base_srv, i) for i in range(4)]

    # --- Bomb sprites (spritesheet animations) ---
    bomb_size = int(cs * 3.0)  # Bomb size (larger for visibility)
    _cache["bomb_idle"] = _sheet(f"{BASE}/Bomb/idel 50px 50.png",
                                 50, 50, max_frames=3, target=(bomb_size, bomb_size))
    _cache["bomb_explode"] = _sheet(f"{BASE}/Bomb/expl 50px 50.png",
                                    50, 50, max_frames=11, target=(bomb_size, bomb_size))

    # --- Trojan (Skeleton Warrior spritesheet: 624×240, 5 rows × 48×48 frames) ---
    trojan_size = int(spr_size * 2.0)  # Trojan bigger than basic malware
    trojan_t = (trojan_size, trojan_size)
    path = f"{BASE}/malware/Trojan/Skeleton Warrior.png"

    # Row 1: Attack (13 frames)
    _cache["trojan_Attack"] = _sheet_row(path, 48, 48, row_idx=1, max_frames=13, target=trojan_t)

    # Row 2: Walk (6 frames)
    _cache["trojan_Run"] = _sheet_row(path, 48, 48, row_idx=2, max_frames=6, target=trojan_t)

    # Row 4: Death (13 frames)
    _cache["trojan_Die"] = _sheet_row(path, 48, 48, row_idx=4, max_frames=13, target=trojan_t)

    # Fallback sprite
    _cache["trojan"] = _cache.get("trojan_Run", [pygame.Surface((trojan_size, trojan_size))])

    # --- Spyware (16 individual PNG frames, 4 rows × 4 frames) ---
    spyware_size = int(spr_size * 1.5)  # Larger spyware
    spyware_frames = []
    for i in range(16):
        frame_path = f"{BASE}/malware/Spyware/PNG/frame{i:04d}.png"
        try:
            frame = pygame.image.load(frame_path).convert_alpha()
            frame = pygame.transform.scale(frame, (spyware_size, spyware_size))
            spyware_frames.append(frame)
        except:
            pass
    _cache["spyware"] = spyware_frames if spyware_frames else [pygame.Surface((spyware_size, spyware_size), pygame.SRCALPHA)]

    # Spyware attack effect (Plant1_Attack_swing.png - spritesheet: 4 rows × 3 frames, use first row only)
    # Spritesheet: 448×256 = 3 cols (149px) × 4 rows (64px)
    attack_sprite_path = f"{BASE}/malware/Spyware/Plant1_Attack_swing.png"
    try:
        spyware_attack_frames = _sheet_row(attack_sprite_path, 149, 64, row_idx=0, max_frames=3, target=(twr_size, twr_size))
        _cache["spyware_attack"] = spyware_attack_frames if spyware_attack_frames else []
    except Exception as e:
        print(f"Failed to load spyware attack frames: {e}")
        _cache["spyware_attack"] = []

    # --- SlowSpy (16 individual PNG frames, same as Spyware) ---
    slowspy_size = int(spr_size * 1.5)  # Same size as Spyware
    slowspy_frames = []
    for i in range(16):
        frame_path = f"{BASE}/malware/SlowSpy/PNG/frame{i:04d}.png"
        try:
            frame = pygame.image.load(frame_path).convert_alpha()
            frame = pygame.transform.scale(frame, (slowspy_size, slowspy_size))
            slowspy_frames.append(frame)
        except:
            pass
    _cache["slowspy"] = slowspy_frames if slowspy_frames else [pygame.Surface((slowspy_size, slowspy_size), pygame.SRCALPHA)]

    # --- LightSpy (16 individual PNG frames, same as Spyware) ---
    lightspy_size = int(spr_size * 1.5)  # Same size as Spyware
    lightspy_frames = []
    for i in range(16):
        frame_path = f"{BASE}/malware/LightSpy/PNG/frame{i:04d}.png"
        try:
            frame = pygame.image.load(frame_path).convert_alpha()
            frame = pygame.transform.scale(frame, (lightspy_size, lightspy_size))
            lightspy_frames.append(frame)
        except:
            pass
    _cache["lightspy"] = lightspy_frames if lightspy_frames else [pygame.Surface((lightspy_size, lightspy_size), pygame.SRCALPHA)]

    # LightSpy attack effect (same as Spyware)
    lightspy_attack_path = f"{BASE}/malware/LightSpy/Plant1_Attack_swing.png"
    try:
        lightspy_attack_frames = _sheet_row(lightspy_attack_path, 149, 64, row_idx=0, max_frames=3, target=(twr_size, twr_size))
        _cache["lightspy_attack"] = lightspy_attack_frames if lightspy_attack_frames else []
    except Exception as e:
        print(f"Failed to load lightspy attack frames: {e}")
        _cache["lightspy_attack"] = []

    # --- Ransomware (Golem_1 spritesheet: Attack 990×64, Die 1170×64, Walk 900×64) ---
    ransomware_size = int(spr_size * 2.5)  # Bigger than normal malware
    rw_size = (ransomware_size, ransomware_size)

    # Attack animation (15 frames at 66×64 each)
    _cache["ransomware_Attack"] =_load_spaced_frames(f"{BASE}/malware/Ransomware/Golem_1_attack.png",
                                         64, 64,frame_spacing=90, num_frames=11, target_size=rw_size)

    # Die animation (18 frames at 65×64 each)
    _cache["ransomware_Die"] = _load_spaced_frames(f"{BASE}/malware/Ransomware/Golem_1_die.png",
                                      64, 64, frame_spacing=90, num_frames=13, target_size=rw_size)

    # Walk/Run animation (15 frames at 60×64 each)
    _cache["ransomware_Run"] = _load_spaced_frames(f"{BASE}/malware/Ransomware/Golem_1_walk.png",
                                      64, 64, frame_spacing=90, num_frames=10, target_size=rw_size)

    # Fallback sprite
    _cache["ransomware"] = _cache.get("ransomware_Run", [pygame.Surface((ransomware_size, ransomware_size))])

    # --- Worm / Plant3 (64×64 mỗi frame, 4 hướng: up/down/left/right) ---
    worm_size = int(spr_size * 1.8)  # Worm bigger than other malware
    worm_t = (worm_size, worm_size)
    _worm_action_frames = {"Walk": 6, "Run": 8, "Attack": 7, "Idle": 4, "Death": 10, "Hurt": 5}
    _worm_directions = ["up", "down", "left", "right"]

    for action, n in _worm_action_frames.items():
        path = f"{BASE}/malware/Worm/Plant3/{action}/Plant3_{action}_full.png"
        # Load sheet (64×64 mỗi frame, 8 cột × 4 dòng)
        all_frames = _sheet(path, 64, 64, max_frames=n*4, target=worm_t)

        # Chia thành 4 hướng
        for dir_idx, direction in enumerate(_worm_directions):
            start = dir_idx * n
            end = start + n
            _cache[f"worm_{action}_{direction}"] = all_frames[start:end] if len(all_frames) >= end else all_frames

        # Fallback
        _cache[f"worm_{action}"] = _cache.get(f"worm_{action}_right", all_frames[:n])

    _cache["worm"] = _cache.get("worm_Run_right", [pygame.Surface((spr_size, spr_size))])

    # --- WormPoison / Plant2 (64×64 mỗi frame, 4 hướng: up/down/left/right) ---
    worm_poison_size = int(spr_size * 1.8)  # Same size as regular Worm
    worm_poison_t = (worm_poison_size, worm_poison_size)
    _worm_poison_action_frames = {"Walk": 6, "Run": 8, "Attack": 7, "Idle": 4, "Death": 10, "Hurt": 5}
    _worm_poison_directions = ["up", "down", "left", "right"]

    for action, n in _worm_poison_action_frames.items():
        path = f"{BASE}/malware/WormPoison/Plant2/{action}/Plant2_{action}_full.png"
        # Load sheet (64×64 mỗi frame, 8 cột × 4 dòng)
        all_frames = _sheet(path, 64, 64, max_frames=n*4, target=worm_poison_t)

        # Chia thành 4 hướng
        for dir_idx, direction in enumerate(_worm_poison_directions):
            start = dir_idx * n
            end = start + n
            _cache[f"worm_poison_{action}_{direction}"] = all_frames[start:end] if len(all_frames) >= end else all_frames

        # Fallback
        _cache[f"worm_poison_{action}"] = _cache.get(f"worm_poison_{action}_right", all_frames[:n])

    _cache["worm_poison"] = _cache.get("worm_poison_Run_right", [pygame.Surface((spr_size, spr_size))])

    # --- TrojanRanged (Skeleton Mage spritesheet: 1008×240, 5 rows × 48×48 frames) ---
    trojan_ranged_size = int(spr_size * 2.0)  # Bigger than normal malware
    tr_size = (trojan_ranged_size, trojan_ranged_size)
    path = f"{BASE}/malware/TrojanRanged/Skeleton Mage.png"

    # Row 1: Attack (21 frames)
    _cache["trojan_ranged_Attack"] = _sheet_row(path, 48, 48, row_idx=1, max_frames=21, target=tr_size)

    # Row 2: Walk/Fly (6 frames)
    _cache["trojan_ranged_Run"] = _sheet_row(path, 48, 48, row_idx=2, max_frames=6, target=tr_size)

    # Row 4: Death (18 frames)
    _cache["trojan_ranged_Die"] = _sheet_row(path, 48, 48, row_idx=4, max_frames=18, target=tr_size)

    # Fallback sprite
    _cache["trojan_ranged"] = _cache.get("trojan_ranged_Run", [pygame.Surface((trojan_ranged_size, trojan_ranged_size))])

    # --- VaultWare (Gollux spritesheet: Attack 7296×128, Run 3072×128, spaced 384px apart) ---
    vaultware_size = int(spr_size * 3)  # Bigger than normal malware
    vw_size = (vaultware_size, vaultware_size)

    # Attack animation (19 frames, 128×128 each, spaced 384px apart = 128 frame + 256 padding)
    _cache["vaultware_Attack"] = _load_spaced_frames(f"{BASE}/malware/VaultWare/gollux_attack_B.png",
                                                     128, 128, frame_spacing=384, num_frames=19, target_size=vw_size)

    # Run/Walk animation (8 frames, 128×128 each, spaced 384px apart = 128 frame + 256 padding)
    _cache["vaultware_Run"] = _load_spaced_frames(f"{BASE}/malware/VaultWare/gollux_move.png",
                                                  128, 128, frame_spacing=384, num_frames=8, target_size=vw_size)

    # Fallback sprite
    _cache["vaultware"] = _cache.get("vaultware_Run", [pygame.Surface((vaultware_size, vaultware_size))])

    # --- RiposteWare animations (8 frames mỗi action, spaced 384px) ---
      # RiposteWare size
    riposteware_size = int(spr_size * 2)
    rw_size = (riposteware_size, riposteware_size)
    # Attack animation (8 frames, 128×128 each, spaced 384px apart)
    _cache["riposteware_Attack"] = _load_spaced_frames(f"{BASE}/malware/RiposteWare/frogger_tongue.png",
                                                       128, 128, frame_spacing=384, num_frames=8, target_size=rw_size)

    # Run/Walk animation (8 frames, 128×128 each, spaced 384px apart)
    _cache["riposteware_Run"] = _load_spaced_frames(f"{BASE}/malware/RiposteWare/frogger_move.png",
                                                    128, 128, frame_spacing=384, num_frames=8, target_size=rw_size)

    # Fallback sprite
    _cache["riposteware"] = _cache.get("riposteware_Run", [pygame.Surface((riposteware_size, riposteware_size))])

    # --- FireWorm (Boss Level 1: spritesheet with walk/attack animations) ---
    fireworm_size = int(spr_size * 3.5)  # Boss is much larger than malware
    fw_size = (fireworm_size, fireworm_size)

    # Try to load FireWorm animations from data/sprites/Boss/FireWorm
    try:
        # Walk/Run animation (default)
        fireworm_walk_path = f"{BASE}/Boss/FireWorm/Walk.png"
        _cache["fireworm_Walk"] = _sheet(fireworm_walk_path, 90, 64, max_frames=9, target=fw_size)
    except:
        _cache["fireworm_Walk"] = [pygame.Surface(fw_size, pygame.SRCALPHA)]

    try:
        # Attack animation
        fireworm_attack_path = f"{BASE}/Boss/FireWorm/Attack.png"
        _cache["fireworm_Attack"] = _sheet(fireworm_attack_path, 90, 64, max_frames=16, target=fw_size)
    except:
        _cache["fireworm_Attack"] = _cache.get("fireworm_Walk", [pygame.Surface(fw_size, pygame.SRCALPHA)])

    try:
        # Die animation
        fireworm_die_path = f"{BASE}/Boss/FireWorm/Die.png"
        _cache["fireworm_Die"] = _sheet(fireworm_die_path, 90, 64, max_frames=8, target=fw_size)
    except:
        _cache["fireworm_Die"] = _cache.get("fireworm_Walk", [pygame.Surface(fw_size, pygame.SRCALPHA)])

    # Fallback sprite (use Walk by default)
    _cache["fireworm"] = _cache.get("fireworm_Walk", [pygame.Surface(fw_size, pygame.SRCALPHA)])

    # --- FlyingDemon (Boss Level 2: spritesheet with attack/flying/death animations) ---
    flyingdemon_size = int(spr_size * 3.5)  # Boss is much larger than malware
    fd_size = (flyingdemon_size, flyingdemon_size)

    # Try to load FlyingDemon animations from data/sprites/Boss/FlyingDemon
    try:
        # Flying/Move animation (default)
        flyingdemon_flying_path = f"{BASE}/Boss/FlyingDemon/Flying.png"
        _cache["flyingdemon_Flying"] = _sheet(flyingdemon_flying_path, 81, 64, max_frames=4, target=fd_size)
    except:
        _cache["flyingdemon_Flying"] = [pygame.Surface(fd_size, pygame.SRCALPHA)]

    try:
        # Attack animation (drop bomb)
        flyingdemon_attack_path = f"{BASE}/Boss/FlyingDemon/Attack.png"
        _cache["flyingdemon_Attack"] = _sheet(flyingdemon_attack_path, 81, 64, max_frames=8, target=fd_size)
    except:
        _cache["flyingdemon_Attack"] = _cache.get("flyingdemon_Flying", [pygame.Surface(fd_size, pygame.SRCALPHA)])

    try:
        # Death animation
        flyingdemon_death_path = f"{BASE}/Boss/FlyingDemon/Death.png"
        _cache["flyingdemon_Die"] = _sheet(flyingdemon_death_path, 81, 64, max_frames=6, target=fd_size)
    except:
        _cache["flyingdemon_Die"] = _cache.get("flyingdemon_Flying", [pygame.Surface(fd_size, pygame.SRCALPHA)])

    # Fallback sprite (use Flying by default)
    _cache["flyingdemon"] = _cache.get("flyingdemon_Flying", [pygame.Surface(fd_size, pygame.SRCALPHA)])

    # --- FlyingDemon Attack Effect (Purple ring + tail particles, chồng trên boss) ---
    attack_effect_size = int(spr_size * 4.0)  # Lớn hơn boss, dễ thấy
    attack_effect_frames = _create_attack_effect(attack_effect_size, num_frames=12)
    _cache["flyingdemon_attack_effect"] = attack_effect_frames if attack_effect_frames else [pygame.Surface((attack_effect_size, attack_effect_size), pygame.SRCALPHA)]

    # --- Shadow (Boss Level 4: walk/attack/death/roll animations, 247x87 per frame) ---
    shadow_size = int(spr_size * 3.5)
    sh_size = (shadow_size, shadow_size)
    shadow_base = f"{BASE}/Boss/Shadow"

    try:
        _cache["shadow_Walk"] = _sheet(f"{shadow_base}/walk.png", 247, 80, max_frames=14, target=sh_size)
    except Exception:
        _cache["shadow_Walk"] = [pygame.Surface(sh_size, pygame.SRCALPHA)]

    try:
        _cache["shadow_Attack"] = _sheet(f"{shadow_base}/Attack 1.png", 247, 80, max_frames=10, target=sh_size)
    except Exception:
        _cache["shadow_Attack"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    try:
        _cache["shadow_Die"] = _sheet(f"{shadow_base}/death.png", 247, 80, max_frames=33, target=sh_size)
    except Exception:
        _cache["shadow_Die"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    try:
        _cache["shadow_Roll_Pre"] = _sheet(f"{shadow_base}/Roll/Pre-Attack 3.png", 247, 80, max_frames=3, target=sh_size)
    except Exception:
        _cache["shadow_Roll_Pre"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    try:
        _cache["shadow_Roll_Mid"] = _sheet(f"{shadow_base}/Roll/mid-Attack 3.png", 247, 87, max_frames=4, target=sh_size)
    except Exception:
        _cache["shadow_Roll_Mid"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    try:
        _cache["shadow_Roll_End"] = _sheet(f"{shadow_base}/Roll/end-Attack 3.png", 247, 87, max_frames=7, target=sh_size)
    except Exception:
        _cache["shadow_Roll_End"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    _cache["shadow"] = _cache.get("shadow_Walk", [pygame.Surface(sh_size, pygame.SRCALPHA)])

    # --- Final Boss (Level 5: single SPRITE_SHEET.png, 32x32 per frame) ---
    final_size = int(spr_size * 4.0)
    final_f = (final_size, final_size)
    final_sheet = f"{BASE}/Boss/Final/SPRITE_SHEET.png"

    _cache["final_Walk"]      = _sheet_row(final_sheet, 32, 32, row_idx=1,  max_frames=8,  target=final_f)
    _cache["final_Attack"]    = _sheet_row(final_sheet, 32, 32, row_idx=3,  max_frames=7,  target=final_f)
    _cache["final_Die"]       = _sheet_row(final_sheet, 32, 32, row_idx=6,  max_frames=10, target=final_f)
    _cache["final_Destroy_1"] = _sheet_row(final_sheet, 32, 32, row_idx=9,  max_frames=10, target=final_f)
    _cache["final_Destroy_2"] = _sheet_row(final_sheet, 32, 32, row_idx=10, max_frames=10, target=final_f)
    _cache["final"] = _cache.get("final_Walk", [pygame.Surface(final_f, pygame.SRCALPHA)])

    # --- Tower slow effects (Ice VFX 2: Start/Active/Ending - spritesheets 32x32) ---
    slow_effect_size = int(cs * 2.0)  # Size for tower effects
    slow_base_path = f"{BASE}/tower/slow"
    for stage, frame_count in [("Start", 9), ("Active", 8), ("Ending", 18)]:
        stage_key = stage.lower()
        try:
            frames = _sheet(f"{slow_base_path}/Ice VFX 2 {stage}.png", 32, 32, max_frames=frame_count, target=(slow_effect_size, slow_effect_size))
            _cache[f"tower_slow_{stage_key}"] = frames if frames else [pygame.Surface((slow_effect_size, slow_effect_size), pygame.SRCALPHA)]
        except:
            _cache[f"tower_slow_{stage_key}"] = [pygame.Surface((slow_effect_size, slow_effect_size), pygame.SRCALPHA)]

    # --- Fire mark effect (Explosion 2 SpriteSheet: 18 frames, 48x48 each) ---
    fire_mark_size = int(cs * 2.5)  # Fire mark size (larger for visibility)
    try:
        fire_frames = _sheet(f"{BASE}/tower/FireNode/Explosion 2 SpriteSheet.png", 48, 48, max_frames=18, target=(fire_mark_size, fire_mark_size))
        _cache["fire_mark"] = fire_frames if fire_frames else [pygame.Surface((fire_mark_size, fire_mark_size), pygame.SRCALPHA)]
        # Cache animation phase subsets for easy access
        _cache["fire_mark_appear"] = fire_frames[7:12] if len(fire_frames) >= 12 else fire_frames  # Frames 7-11
        _cache["fire_mark_disappear"] = fire_frames[12:18] if len(fire_frames) >= 18 else fire_frames  # Frames 12-17
    except Exception as e:
        print(f"Warning: Failed to load fire mark frames: {e}")
        _cache["fire_mark"] = [pygame.Surface((fire_mark_size, fire_mark_size), pygame.SRCALPHA)]
        _cache["fire_mark_appear"] = [pygame.Surface((fire_mark_size, fire_mark_size), pygame.SRCALPHA)]
        _cache["fire_mark_disappear"] = [pygame.Surface((fire_mark_size, fire_mark_size), pygame.SRCALPHA)]

    # --- LightSpy Shock Effect (14 frames from Thunder splash spritesheet, use frames 8-14) ---
    shock_effect_size = int(cs * 2.5)  # Shock effect size (same as fire mark)
    try:
        # Tải toàn bộ 14 frames từ spritesheet
        shock_frames = _sheet(f"{BASE}/malware/LightSpy/Thunder splash w blur.png",
                              fw=48, fh=48, max_frames=14,
                              target=(shock_effect_size, shock_effect_size))

        # Sử dụng frames 8-13 (indices 8-13, 6 frames)
        shock_animation = shock_frames[6:14] if len(shock_frames) >= 14 else shock_frames

        # Tạo ping-pong sequence: 8→9→10→11→12→13→12→11→10→9→8
        pong_sequence = shock_animation + shock_animation[-1:0:-1] if len(shock_animation) > 1 else shock_animation

        _cache["shock_effect"] = pong_sequence if pong_sequence else [pygame.Surface((shock_effect_size, shock_effect_size), pygame.SRCALPHA)]
    except Exception as e:
        print(f"Warning: Failed to load shock effect frames: {e}")
        _cache["shock_effect"] = [pygame.Surface((shock_effect_size, shock_effect_size), pygame.SRCALPHA)]

    # --- Tower Stun Animation (13 frames from Thunderstrike w blur.png, plays once) ---
    stun_effect_size = int(cs * 3.5)  # Stun effect size for tower
    try:
        stun_frames = _sheet(f"{BASE}/tower/stun/Thunderstrike w blur.png",
                             fw=64, fh=64, max_frames=13,
                             target=(stun_effect_size, stun_effect_size))
        _cache["tower_stun"] = stun_frames if stun_frames else [pygame.Surface((stun_effect_size, stun_effect_size), pygame.SRCALPHA)]
    except Exception as e:
        print(f"Warning: Failed to load tower stun frames: {e}")
        _cache["tower_stun"] = [pygame.Surface((stun_effect_size, stun_effect_size), pygame.SRCALPHA)]


def get(name: str):
    """Lấy sprite đã load từ cache theo tên key.

    Args:
        name (str): Tên sprite key (vd. "trojan_Run", "tower_basic", "proj_ice").

    Returns:
        pygame.Surface | list[pygame.Surface] | None:
            Surface đơn (tower, projectile), list frame (animated sprite),
            hoặc None nếu key không tồn tại trong cache.
    """
    return _cache.get(name)


def get_temp_wall():
    """Lấy sprite tường tạm thời (đỏ, variant cuối cùng của WALL_FILES)."""
    walls = _cache.get("wall")
    if walls and len(walls) >= 3:
        return walls[2]  # Red wall (Screenshot 2026-04-22 014510.png)
    return None


def action_frame_count(key: str) -> int:
    """Trả về số frame của một sprite key trong cache.

    Args:
        key (str): Tên sprite key cần kiểm tra.

    Returns:
        int: Số frame nếu key tồn tại và là list. 4 nếu không tìm thấy (fallback mặc định).
    """
    frames = _cache.get(key)
    return len(frames) if frames else 4


# ---------------------------------------------------------------------------
# Helpers: image loading
# ---------------------------------------------------------------------------

def _load_spaced_frames(path: str, frame_width: int, frame_height: int,
                       frame_spacing: int, num_frames: int, target_size: tuple,plus=True) -> list:
    """Load frames từ spritesheet với spacing/padding giữa các frame.

    Args:
        path (str): Đường dẫn spritesheet.
        frame_width (int): Chiều rộng mỗi frame.
        frame_height (int): Chiều cao mỗi frame.
        frame_spacing (int): Tổng khoảng cách giữa frame (frame_width + padding).
        num_frames (int): Số frame cần load.
        target_size (tuple): Kích thước đích (w, h).

    Returns:
        list: Danh sách pygame.Surface đã scale.
    """
    try:
        img = pygame.image.load(path).convert_alpha()
    except:
        return [pygame.Surface(target_size, pygame.SRCALPHA)]

    frames = []
    for i in range(num_frames):
        if plus:
            x = i * frame_spacing + (frame_spacing - frame_width) // 2  # Mạc giữa frame_spacing - frame_width
        else: x = i * frame_spacing  # Mỗi frame cách nhau frame_spacing pixels
        try:
            # Crop frame từ spritesheet
            frame_surface = img.subsurface((x, 0, frame_width, frame_height))
            # Scale đến target size
            frame_surface = pygame.transform.scale(frame_surface, target_size)
            frames.append(frame_surface)
        except:
            frames.append(pygame.Surface(target_size, pygame.SRCALPHA))

    return frames if frames else [pygame.Surface(target_size, pygame.SRCALPHA)]


def _create_attack_effect(size: int, num_frames: int = 12) -> list:
    """Tạo animated purple ring + tail effect khi boss drop bomb hoặc attack server.

    Effect: Vòng tím phát triển từ giữa ra ngoài, với tail particles rải rác quanh vòng.
    Animation smooth từ frame 0 (nhỏ) -> frame end (lớn, fade out).

    Args:
        size (int): Kích thước surface (size × size).
        num_frames (int): Số frame animation (mặc định 12).

    Returns:
        list[pygame.Surface]: Danh sách frame animation SRCALPHA.
    """
    import math

    frames = []
    mid = size // 2
    ring_color = (180, 100, 255)  # Purple ring
    tail_color = (200, 150, 255)  # Lighter purple for tail

    for frame_idx in range(num_frames):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)

        # Progress từ 0.0 (start) -> 1.0 (end)
        progress = frame_idx / max(1, num_frames - 1)

        # Ring: bắt đầu từ bán kính nhỏ, phát triển ra (radius tăng theo progress)
        ring_radius_min = int(size * 0.15)  # Bắt đầu từ 15% của size
        ring_radius_max = int(size * 0.45)  # Kết thúc ở 45%
        ring_radius = int(ring_radius_min + (ring_radius_max - ring_radius_min) * progress)

        # Ring width: mỏng dần theo progress (4px -> 1px)
        ring_width = max(1, 4 - int(3 * progress))

        # Ring alpha: màu chính toàn độ, nhưng mờ dần ở cuối
        ring_alpha = int(255 * (1.0 - progress * 0.7))
        ring_color_alpha = (*ring_color, ring_alpha)

        # Vẽ ring chính
        pygame.draw.circle(surf, ring_color_alpha, (mid, mid), ring_radius, ring_width)

        # Vẽ ring thứ 2 (glow effect): lớn hơn một chút, mờ hơn
        glow_radius = ring_radius + ring_width + 2
        glow_alpha = int(ring_alpha * 0.5)
        glow_color = (*ring_color, glow_alpha)
        pygame.draw.circle(surf, glow_color, (mid, mid), glow_radius, 1)

        # Tail effect: tail particles rải rác quanh ring (nhiều lên theo progress)
        num_tails = 8 + int(6 * progress)  # Số tail tăng dần
        for tail_idx in range(num_tails):
            # Góc đều nhau quanh vòng
            angle = (tail_idx / num_tails) * 2 * math.pi
            # Tail position: trên ring
            tail_dist = ring_radius + 4
            tail_x = mid + int(tail_dist * math.cos(angle))
            tail_y = mid + int(tail_dist * math.sin(angle))

            # Tail size: nhỏ, giảm dần
            tail_size = max(1, 3 - int(2 * progress))
            tail_alpha = int(ring_alpha * 0.7)
            tail_color_alpha = (*tail_color, tail_alpha)

            # Vẽ tail particle
            if tail_size > 0:
                pygame.draw.circle(surf, tail_color_alpha, (tail_x, tail_y), tail_size)

        frames.append(surf)

    return frames if frames else [pygame.Surface((size, size), pygame.SRCALPHA)]


def _img(path: str, w: int, h: int) -> pygame.Surface:
    """Load và scale một ảnh đơn từ file. Trả về placeholder màu magenta nếu lỗi.

    Args:
        path (str): Đường dẫn file ảnh (PNG/JPG).
        w (int): Chiều rộng đích sau khi scale (pixel).
        h (int): Chiều cao đích sau khi scale (pixel).

    Returns:
        pygame.Surface: Surface đã scale đúng kích thước (w × h).
            Surface magenta bán trong suốt (200, 0, 200, 160) nếu file không tìm thấy.
    """
    try:
        return pygame.transform.scale(
            pygame.image.load(path).convert_alpha(), (w, h)
        )
    except Exception:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill((200, 0, 200, 160))
        return s


def _sheet(path: str, fw: int, fh: int,
           max_frames: int = 999,
           target: tuple = None) -> list:
    """Slice spritesheet thành danh sách frame Surface, tùy chọn scale.

    Đọc ảnh spritesheet và cắt thành các frame theo kích thước fw × fh.
    Frame đi từ trái sang phải, trên xuống dưới.

    Args:
        path (str): Đường dẫn file spritesheet.
        fw (int): Chiều rộng mỗi frame trong sheet (pixel).
        fh (int): Chiều cao mỗi frame trong sheet (pixel).
        max_frames (int): Số frame tối đa cần lấy. Mặc định 999 (lấy tất cả).
        target (tuple | None): (w, h) kích thước đích sau khi scale.
            None = giữ nguyên kích thước gốc fw × fh.

    Returns:
        list[pygame.Surface]: Danh sách frame Surface đã scale (nếu có target).
            List chứa 1 placeholder magenta nếu file không tìm thấy.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        dummy = pygame.Surface(target or (fw, fh), pygame.SRCALPHA)
        dummy.fill((200, 0, 200, 160))
        return [dummy]

    cols   = max(1, sheet.get_width()  // fw)
    rows   = max(1, sheet.get_height() // fh)
    count  = min(cols * rows, max_frames)
    frames = []
    for i in range(count):
        col  = i % cols
        row  = i // cols
        sub  = sheet.subsurface(pygame.Rect(col * fw, row * fh, fw, fh))
        if target:
            sub = pygame.transform.scale(sub, target)
        frames.append(sub)
    return frames or [pygame.Surface(target or (fw, fh), pygame.SRCALPHA)]


def _sheet_row(path: str, fw: int, fh: int, row_idx: int,
               max_frames: int = 999, target: tuple = None) -> list:
    """Lấy một hàng cụ thể từ spritesheet grid.

    Args:
        path (str): Đường dẫn file spritesheet.
        fw (int): Chiều rộng mỗi frame.
        fh (int): Chiều cao mỗi frame.
        row_idx (int): Chỉ số hàng (0-indexed).
        max_frames (int): Số frame tối đa từ hàng này.
        target (tuple | None): Kích thước scale đích.

    Returns:
        list[pygame.Surface]: Frame từ hàng được chỉ định.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
    except Exception:
        dummy = pygame.Surface(target or (fw, fh), pygame.SRCALPHA)
        dummy.fill((200, 0, 200, 160))
        return [dummy]

    cols = max(1, sheet.get_width() // fw)
    frames = []
    for col in range(cols):
        if len(frames) >= max_frames:
            break
        x = col * fw
        y = row_idx * fh
        rect = pygame.Rect(x, y, fw, fh)

        if rect.right <= sheet.get_width() and rect.bottom <= sheet.get_height():
            sub = sheet.subsurface(rect)
            if target:
                sub = pygame.transform.scale(sub, target)
            frames.append(sub)

    return frames or [pygame.Surface(target or (fw, fh), pygame.SRCALPHA)]


def _pulse_tint(base: pygame.Surface, frame: int) -> pygame.Surface:
    """Tạo hiệu ứng glow pulse nhẹ cho server sprite theo frame number.

    Args:
        base (pygame.Surface): Surface gốc của server sprite.
        frame (int): Chỉ số frame (0-3) — xác định cường độ glow theo sin.

    Returns:
        pygame.Surface: Bản sao của base với lớp tint cyan nhạt đè lên.
            Cường độ tint dao động theo sin(frame × π/2).
    """
    s     = base.copy()
    pulse = int(abs(math.sin(frame * math.pi / 2)) * 35)
    tint  = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    tint.fill((0, pulse, pulse // 2, 0))
    s.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    return s


# ---------------------------------------------------------------------------
# Map tiles
# ---------------------------------------------------------------------------
PATH_FILES = ["Screenshot 2026-04-22 014150.png", "Screenshot 2026-04-22 014317.png"] 
WALL_FILES = ["Screenshot 2026-04-22 014353.png","Screenshot 2026-04-22 014438.png", "Screenshot 2026-04-22 014510.png"]
def _load_map_tiles(cs: int) -> None:
    """Load tile ảnh cho PATH và WALL từ thư mục data/sprites/Map/.

    Xử lý ảnh PATH (2 biến thể, overlay tối nhẹ) và WALL (3 biến thể,
    tạo hiệu ứng pseudo-3D bằng cách kéo dài thân tường theo TALL_FACTOR).
    Kết quả lưu vào _cache["path"] và _cache["wall"].

    Args:
        cs (int): Kích thước ô lưới (pixel) — settings.CELL_SIZE.

    Side effects:
        - Lưu list Surface vào _cache["path"] và _cache["wall"].
        - Nếu load thất bại → lưu list Surface trống làm fallback.

    Note:
        Gọi bởi init() sau pygame.display.set_mode() để convert_alpha() hoạt động.
        TALL_FACTOR (settings) xác định chiều cao thân tường so với cs.
    """
    try:
        # --- 1. XỬ LÝ PATH (2 ảnh, trọng số ngang nhau 50-50) ---
        path_variants = []
        for f_name in PATH_FILES:
            full_path = os.path.join(BASE, "Map", f_name)
            img = pygame.image.load(full_path).convert_alpha()
            img = pygame.transform.scale(img, (cs, cs))
            
            dark = pygame.Surface((cs, cs))
            dark.fill((20, 18, 28))
            dark.set_alpha(80)
            img.blit(dark, (0, 0))
            
            path_variants.append(img)
        wall_variants = []
        for f_name in WALL_FILES:
            if f_name == "Screenshot 2026-04-22 014510.png": 
                r=130
                g=10
                b=10
                b_r=150
                b_g=15
                b_b=15
            else:
                r=15
                g=15
                b=25
                b_r=30
                b_g=35
                b_b=50
                
            full_walls = os.path.join(BASE, "Map", f_name)
            
            w_img = pygame.image.load(full_walls).convert_alpha()
            w_img = pygame.transform.scale(w_img, (cs, cs))
        
            tall_h = int(cs * settings.TALL_FACTOR)
            body_h = tall_h - cs
            tall_wall = pygame.Surface((cs, tall_h), pygame.SRCALPHA)
        
            # --- CÁCH MỚI: DÙNG TEXTURE CỦA ẢNH GỐC LÀM THÂN TƯỜNG ---
            
            # Bước 1: Cắt lấy 2 pixel ở vị trí dưới cùng của ảnh nóc (Ảnh gốc)
            bottom_slice = pygame.Rect(0, cs - 20, cs, 20)
            wall_texture = w_img.subsurface(bottom_slice).copy()
            
            # Bước 2: Kéo giãn phần đã cắt xuống bằng chiều cao của thân tường
            wall_body = pygame.transform.scale(wall_texture, (cs, body_h))
            
            # Bước 3: Tạo một lớp màng tối (Overlay) trong suốt
            dark_overlay = pygame.Surface((cs, body_h), pygame.SRCALPHA)
            dark_overlay.fill((r, g, b, 180)) # Đặt Alpha khoảng 180-220 để thấy vân gạch bên dưới
            
            # Bước 4: Phủ lớp màng tối lên thân tường và vẽ viền
            wall_body.blit(dark_overlay, (0, 0))
            pygame.draw.rect(wall_body, (b_r, b_g, b_b, 200), [0, 0, cs, body_h], 1) # Viền khối
        
            # Bước 5: Lắp ghép thân và nóc vào khuôn tổng
            tall_wall.blit(wall_body, (0, cs)) # Thân dưới
            tall_wall.blit(w_img, (0, 0))
            
           
            wall_variants.append(tall_wall)

        # Lưu danh sách vào cache
        _cache["wall"] = wall_variants
        _cache["path"] = path_variants

    except Exception as e:
        print(f"Error loading sprite images: {e}")
        # Fallback nếu lỗi file
        _cache["wall"] = [pygame.Surface((cs, cs))] # Tạo mặt phẳng trống tạm thời
        _cache["path"] = [pygame.Surface((cs, cs))]
def _wall_proc(cs: int) -> pygame.Surface:
    """Tạo procedural wall tile màu xanh đậm làm fallback khi thiếu ảnh.

    Args:
        cs (int): Kích thước ô lưới (pixel).

    Returns:
        pygame.Surface: Surface cs × cs với pattern đường kẻ và vòng tròn trung tâm.
    """
    s   = pygame.Surface((cs, cs))
    mid = cs // 2
    s.fill((12, 52, 62))
    pygame.draw.rect(s, (18, 68, 80), (2, 2, cs-4, cs-4))
    c1, c2 = (0, 155, 175), (0, 200, 220)
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        pygame.draw.line(s, c1, (mid+dx*4, mid+dy*4),
                         (mid+dx*(mid-3), mid+dy*(mid-3)), 1)
    for cx, cy in [(4,4),(cs-5,4),(4,cs-5),(cs-5,cs-5)]:
        pygame.draw.circle(s, c2, (cx, cy), 2)
    pygame.draw.circle(s, (0,120,140), (mid, mid), 5)
    pygame.draw.circle(s, c2,          (mid, mid), 3)
    pygame.draw.rect(s, (28, 95, 110), (0, 0, cs, cs), 1)
    return s


def _path_proc(cs: int) -> pygame.Surface:
    """Tạo procedural path tile màu tím đậm với grid lines làm fallback.

    Args:
        cs (int): Kích thước ô lưới (pixel).

    Returns:
        pygame.Surface: Surface cs × cs với lưới kẻ mờ trên nền tím đậm.
    """
    s    = pygame.Surface((cs, cs))
    grid = (44, 39, 56)
    s.fill((32, 28, 42))
    step = max(8, cs // 5)
    for i in range(0, cs+1, step):
        pygame.draw.line(s, grid, (i, 0), (i, cs), 1)
        pygame.draw.line(s, grid, (0, i), (cs, i), 1)
    return s


# ---------------------------------------------------------------------------
# Procedural projectile fallback
# ---------------------------------------------------------------------------

def _proc_proj(radius: int, inner: tuple, outer: tuple) -> pygame.Surface:
    """Tạo procedural projectile sprite hình tròn glow làm fallback.

    Args:
        radius (int): Bán kính lõi đạn (pixel).
        inner (tuple): Màu RGB lõi trong (vd. (200, 100, 255)).
        outer (tuple): Màu RGBA vòng ngoài glow (vd. (240, 180, 255)).

    Returns:
        pygame.Surface: Surface vuông (radius*3) × (radius*3) với SRCALPHA,
            vẽ vòng ngoài mờ và lõi sáng ở trung tâm.
    """
    size = radius * 3
    s    = pygame.Surface((size, size), pygame.SRCALPHA)
    mid  = size // 2
    pygame.draw.circle(s, (*outer, 80), (mid, mid), radius)
    pygame.draw.circle(s, inner,        (mid, mid), max(1, radius-2))
    return s
