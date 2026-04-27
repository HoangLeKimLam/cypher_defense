# main.py
# Điểm vào (entry point) của chương trình.
# Chỉ làm 1 việc: tạo Game và chạy.
# Chạy bằng lệnh: python main.py

from game import Game


def main():
    """Khởi động Cypher Defense — tạo Game và chạy vòng lặp chính.

    Returns:
        None: Hàm block cho đến khi người chơi thoát game (ESC hoặc đóng cửa sổ).

    Usage:
        Chạy trực tiếp từ terminal::

            python main.py
    """
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
