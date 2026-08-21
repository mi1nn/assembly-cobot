from .config_loader import PoseLoader


def main():
    pose_loader = PoseLoader()

    home = pose_loader.get("home")

    print("HOME pose:")
    print(home)

    print("HOME type:")
    print(home["type"])

    print("HOME position:")
    print(home["position"])


if __name__ == "__main__":
    main()