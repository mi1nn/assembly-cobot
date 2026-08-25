import rclpy
import DR_init


ROBOT_ID = "dsr01"
ROBOT_MODEL = "m0609"


def main(args=None):

    # ROS2 초기화
    rclpy.init(args=args)

    # Doosan 로봇 설정
    DR_init.__dsr__id = ROBOT_ID
    DR_init.__dsr__model = ROBOT_MODEL

    # DSR_ROBOT2에서 사용할 Node 생성
    dsr_node = rclpy.create_node(
        "coordinate_manager_test",
        namespace=ROBOT_ID,
    )

    DR_init.__dsr__node = dsr_node

    try:
        # DR_init 설정 이후 import
        from .coordinate_manager import CoordinateManager

        manager = CoordinateManager()

        # DB에서 받게 될 것과 동일한 형식
        ucs = {
            "p1": [
                448.74,
                -29.40,
                52.58,
                0.0,
                180.0,
                0.0,
            ],
            "p2": [
                548.74,
                -29.40,
                52.58,
                0.0,
                180.0,
                0.0,
            ],
            "p3": [
                448.74,
                70.60,
                52.58,
                0.0,
                180.0,
                0.0,
            ],
        }

        print(
            "\n========== UCS TEST START ==========",
            flush=True,
        )

        # -----------------------------------------------------
        # 1. 사용자 좌표계 생성
        # -----------------------------------------------------

        coord_id = manager.create_from_ucs(ucs)

        print(
            f"[TEST] 생성된 coord_id = {coord_id}",
            flush=True,
        )

        # -----------------------------------------------------
        # 2. get_id() 확인
        # -----------------------------------------------------

        saved_id = manager.get_id()

        print(
            f"[TEST] 저장된 coord_id = {saved_id}",
            flush=True,
        )

        if coord_id != saved_id:
            raise RuntimeError(
                "coord_id 저장 확인 실패"
            )

        # -----------------------------------------------------
        # 3. 같은 P1/P2/P3로 다시 호출
        #
        # 새 좌표계를 생성하지 않고
        # 기존 ID를 반환해야 함
        # -----------------------------------------------------

        reused_id = manager.create_from_ucs(ucs)

        print(
            f"[TEST] 재사용 coord_id = {reused_id}",
            flush=True,
        )

        if coord_id != reused_id:
            raise RuntimeError(
                "UCS 재사용 테스트 실패"
            )

        # -----------------------------------------------------
        # 4. 생성한 사용자 좌표계 기준으로
        #    현재 TCP 위치 확인
        #
        # 로봇은 움직이지 않음
        # -----------------------------------------------------

        current_pose, solution = (
            manager.get_current_pose()
        )

        print(
            f"[TEST] UCS 기준 현재 Pose = "
            f"{current_pose}",
            flush=True,
        )

        print(
            f"[TEST] Solution = {solution}",
            flush=True,
        )

        print(
            "========== UCS TEST SUCCESS ==========\n",
            flush=True,
        )

    except Exception as e:

        print(
            f"[TEST] UCS TEST FAILED: {e}",
            flush=True,
        )

        raise

    finally:

        dsr_node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()