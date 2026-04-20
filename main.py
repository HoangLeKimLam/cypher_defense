# main.py
# Điểm vào (entry point) của chương trình.
# Chỉ làm 1 việc: tạo Game và chạy.
# Chạy bằng lệnh: python main.py

from game import Game


def main():
  game=Game()
  game.run()

  pass


if __name__ == "__main__":
    main()
