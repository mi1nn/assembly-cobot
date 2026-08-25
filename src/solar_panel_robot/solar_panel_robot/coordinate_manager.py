from DSR_ROBOT2 import (
    posx,
    set_user_cart_coord,
    set_ref_coord,
    get_current_posx,
    DR_BASE,
)


class CoordinateManager:
    """
    Doosan 사용자 좌표계 생성 및 관리를 담당한다.

    - DB의 ucs(p1, p2, p3)를 전달받는다.
    - p1을 사용자 좌표계 원점으로 사용한다.
    - 동일한 좌표계는 다시 생성하지 않고 기존 coord_id를 재사용한다.
    """

    def __init__(self):
        # 생성된 사용자 좌표계 ID
        self.coord_id = None

        # 현재 생성된 UCS가 어떤 P1/P2/P3로 만들어졌는지 저장
        self.ucs_signature = None

    # =========================================================
    # Pose 검증
    # =========================================================

    def _validate_pose(
        self,
        pose,
        name,
    ):
        if not isinstance(
            pose,
            (list, tuple),
        ):
            raise ValueError(
                f"{name}은 list 또는 tuple이어야 합니다."
            )

        if len(pose) != 6:
            raise ValueError(
                f"{name}은 [x, y, z, rx, ry, rz] "
                "6개 값이어야 합니다."
            )

        try:
            return [
                float(value)
                for value in pose
            ]

        except (TypeError, ValueError) as e:
            raise ValueError(
                f"{name}의 모든 값은 숫자여야 합니다."
            ) from e

    # =========================================================
    # 사용자 좌표계 생성
    # =========================================================

    def create_from_ucs(
        self,
        ucs,
    ):
        """
        ucs 형식:

        {
            "p1": [x, y, z, rx, ry, rz],
            "p2": [x, y, z, rx, ry, rz],
            "p3": [x, y, z, rx, ry, rz]
        }

        p1을 사용자 좌표계 원점(pos)으로 사용한다.
        """

        if not isinstance(
            ucs,
            dict,
        ):
            raise ValueError(
                "ucs는 dict여야 합니다."
            )

        for key in (
            "p1",
            "p2",
            "p3",
        ):
            if key not in ucs:
                raise ValueError(
                    f"ucs 필드 누락: {key}"
                )

        p1_values = self._validate_pose(
            ucs["p1"],
            "p1",
        )

        p2_values = self._validate_pose(
            ucs["p2"],
            "p2",
        )

        p3_values = self._validate_pose(
            ucs["p3"],
            "p3",
        )

        # 동일한 UCS인지 확인하기 위한 값
        signature = (
            tuple(p1_values),
            tuple(p2_values),
            tuple(p3_values),
        )

        # 이미 같은 좌표계가 생성되어 있다면
        # set_user_cart_coord()를 다시 호출하지 않는다.
        if (
            self.coord_id is not None
            and self.ucs_signature == signature
        ):
            print(
                "[UCS] 기존 사용자 좌표계 재사용 "
                f"id={self.coord_id}",
                flush=True,
            )

            return self.coord_id

        p1 = posx(p1_values)
        p2 = posx(p2_values)
        p3 = posx(p3_values)

        print(
            "[UCS] 사용자 좌표계 생성 시작",
            flush=True,
        )

        print(
            f"[UCS] P1 = {p1_values}",
            flush=True,
        )

        print(
            f"[UCS] P2 = {p2_values}",
            flush=True,
        )

        print(
            f"[UCS] P3 = {p3_values}",
            flush=True,
        )

        # -----------------------------------------------------
        # x1  = p1
        # x2  = p2
        # x3  = p3
        # pos = p1  → P1을 원점으로 사용
        # ref = BASE
        # -----------------------------------------------------

        coord_id = set_user_cart_coord(
            p1,
            p2,
            p3,
            p1,
            DR_BASE,
        )

        if coord_id is None:
            raise RuntimeError(
                "사용자 좌표계 생성 결과가 없습니다."
            )

        coord_id = int(
            coord_id
        )

        if coord_id < 0:
            raise RuntimeError(
                "사용자 좌표계 생성 실패: "
                f"id={coord_id}"
            )

        self.coord_id = coord_id
        self.ucs_signature = signature

        print(
            "[UCS] 사용자 좌표계 생성 완료 "
            f"id={self.coord_id}",
            flush=True,
        )

        return self.coord_id

    # =========================================================
    # 현재 사용자 좌표 ID
    # =========================================================

    def get_id(self):

        if self.coord_id is None:
            raise RuntimeError(
                "생성된 사용자 좌표계가 없습니다."
            )

        return self.coord_id

    # =========================================================
    # 사용자 좌표 기준 현재 위치 확인
    # =========================================================

    def get_current_pose(self):

        coord_id = self.get_id()

        return get_current_posx(
            ref=coord_id
        )