from DSR_ROBOT2 import (
    task_compliance_ctrl,
    release_compliance_ctrl,
    set_desired_force,
    release_force,
    set_ref_coord,
    check_force_condition,

    DR_BASE,
    DR_TOOL,

    DR_AXIS_X,
    DR_AXIS_Y,
    DR_AXIS_Z,
    DR_AXIS_A,
    DR_AXIS_B,
    DR_AXIS_C,

    DR_FC_MOD_REL,
    DR_FC_MOD_ABS,
)


class ForceController:

    # =========================================================
    # Axis / Reference / Mode Map
    # =========================================================

    # force vector의 index
    AXIS_MAP = {
        "x": 0,
        "y": 1,
        "z": 2,
        "a": 3,
        "b": 4,
        "c": 5,
    }

    # check_force_condition()에서 사용하는 축 상수
    FORCE_AXIS_MAP = {
        "x": DR_AXIS_X,
        "y": DR_AXIS_Y,
        "z": DR_AXIS_Z,
        "a": DR_AXIS_A,
        "b": DR_AXIS_B,
        "c": DR_AXIS_C,
    }

    REFERENCE_MAP = {
        "base": DR_BASE,
        "tool": DR_TOOL,
    }

    MODE_MAP = {
        "relative": DR_FC_MOD_REL,
        "absolute": DR_FC_MOD_ABS,
    }


    # =========================================================
    # Compliance
    # =========================================================

    def compliance_on(
        self,
        stiffness=None,
        time=0.0,
        reference="base",
    ):
        """
        Compliance Control 시작

        stiffness 예시:

        {
            "x": 300,
            "z": 500,
        }

        지정하지 않은 축은 기본 stiffness를 사용한다.
        """

        reference = reference.lower()

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        # 기본 stiffness
        stiffness_vector = [
            3000.0,
            3000.0,
            3000.0,
            200.0,
            200.0,
            200.0,
        ]

        # 지정된 축만 stiffness 변경
        if stiffness is not None:

            if not isinstance(stiffness, dict):
                raise TypeError(
                    "stiffness must be a dict. "
                    'Example: {"z": 500}'
                )

            for axis, value in stiffness.items():

                axis = axis.lower()

                if axis not in self.AXIS_MAP:
                    raise ValueError(
                        f"Invalid stiffness axis: {axis}"
                    )

                index = self.AXIS_MAP[axis]

                stiffness_vector[index] = float(value)

        print(
            f"[COMPLIANCE] ON "
            f"stiffness={stiffness_vector}, "
            f"time={time}, "
            f"reference={reference}",
            flush=True,
        )

        # 기준 좌표계 설정
        set_ref_coord(
            self.REFERENCE_MAP[reference]
        )

        result = task_compliance_ctrl(
            stx=stiffness_vector,
            time=time,
        )

        print(
            f"[COMPLIANCE] result={result}",
            flush=True,
        )

        return result


    def compliance_off(self):
        """
        Compliance Control 종료
        """

        print(
            "[COMPLIANCE] OFF",
            flush=True,
        )

        result = release_compliance_ctrl()

        print(
            f"[COMPLIANCE] OFF result={result}",
            flush=True,
        )

        return result


    # =========================================================
    # Force
    # =========================================================

    def force_on(
        self,
        forces,
        time=0.0,
        mode="relative",
        reference="base",
    ):
        """
        Desired Force 적용

        예:

        {"z": -15}

        또는

        {
            "x": 40,
            "z": -10,
            "a": 5,
        }
        """

        mode = mode.lower()
        reference = reference.lower()

        if mode not in self.MODE_MAP:
            raise ValueError(
                f"Invalid force mode: {mode}"
            )

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        if not isinstance(forces, dict):
            raise TypeError(
                "forces must be a dict. "
                'Example: {"z": -15}'
            )

        desired_force = [0.0] * 6
        direction = [0] * 6

        for axis, value in forces.items():

            axis = axis.lower()

            if axis not in self.AXIS_MAP:
                raise ValueError(
                    f"Invalid force axis: {axis}"
                )

            index = self.AXIS_MAP[axis]

            desired_force[index] = float(value)
            direction[index] = 1

        print(
            f"[FORCE] ON "
            f"force={desired_force}, "
            f"direction={direction}, "
            f"mode={mode}, "
            f"reference={reference}",
            flush=True,
        )

        # 기준 좌표계는 compliance_on()에서 설정한 값을 유지한다.
        # Compliance 활성화 이후 set_ref_coord()를 다시 호출하지 않는다.
        result = set_desired_force(
            fd=desired_force,
            dir=direction,
            time=time,
            mod=self.MODE_MAP[mode],
        )

        print(
            f"[FORCE] result={result}",
            flush=True,
        )

        return result


    def force_off(self):
        """
        Desired Force 종료
        """

        print(
            "[FORCE] OFF",
            flush=True,
        )

        result = release_force()

        print(
            f"[FORCE] OFF result={result}",
            flush=True,
        )

        return result


    # =========================================================
    # Force Condition
    # =========================================================

    def check(
        self,
        axis,
        min_force=None,
        max_force=None,
        reference="base",
    ):
        """
        지정한 축의 Force 조건 확인

        예:

        self.force.check(
            axis="z",
            min_force=10,
            reference="base",
        )

        -> |Fz| >= 10N 이면 True

        또는

        self.force.check(
            axis="z",
            min_force=5,
            max_force=15,
        )

        -> 5N <= |Fz| <= 15N 이면 True
        """

        axis = axis.lower()
        reference = reference.lower()

        if axis not in self.FORCE_AXIS_MAP:
            raise ValueError(
                f"Invalid force axis: {axis}"
            )

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        if min_force is None and max_force is None:
            raise ValueError(
                "min_force or max_force must be specified"
            )

        if min_force is not None and min_force < 0:
            raise ValueError(
                "min_force must be >= 0"
            )

        if max_force is not None and max_force < 0:
            raise ValueError(
                "max_force must be >= 0"
            )

        kwargs = {
            "axis": self.FORCE_AXIS_MAP[axis],
            "ref": self.REFERENCE_MAP[reference],
        }

        if min_force is not None:
            kwargs["min"] = float(min_force)

        if max_force is not None:
            kwargs["max"] = float(max_force)

        result = check_force_condition(
            **kwargs
        )

        return result


    # =========================================================
    # All OFF
    # =========================================================

    def all_off(self):
        """
        Force + Compliance Control 모두 종료
        """

        print(
            "[FORCE CONTROL] ALL OFF",
            flush=True,
        )

        force_result = None
        compliance_result = None

        # Force 해제
        try:
            force_result = release_force()

        except Exception as e:

            print(
                f"[FORCE CONTROL] "
                f"force_off error={e}",
                flush=True,
            )

        # Compliance 해제
        try:
            compliance_result = (
                release_compliance_ctrl()
            )

        except Exception as e:

            print(
                f"[FORCE CONTROL] "
                f"compliance_off error={e}",
                flush=True,
            )

        print(
            f"[FORCE CONTROL] "
            f"force_off={force_result}, "
            f"compliance_off={compliance_result}",
            flush=True,
        )

        return (
            force_result,
            compliance_result,
        )