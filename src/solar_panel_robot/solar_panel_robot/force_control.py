from DSR_ROBOT2 import (
    task_compliance_ctrl,
    release_compliance_ctrl,
    set_desired_force,
    release_force,
    set_ref_coord,
    DR_BASE,
    DR_TOOL,
    DR_FC_MOD_REL,
    DR_FC_MOD_ABS,
)


class ForceController:

    AXIS_MAP = {
        "x": 0,
        "y": 1,
        "z": 2,
        "a": 3,
        "b": 4,
        "c": 5,
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
        stiffness 예시:

        {
            "x": 300,
            "y": 8000,
            "z": 8000,
            "a": 800,
            "b": 800,
            "c": 800,
        }
        """

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        # 기본 stiffness
        stiffness_vector = [
            3000,
            3000,
            3000,
            200,
            200,
            200,
        ]

        # 지정된 축만 변경
        if stiffness is not None:

            for axis, value in stiffness.items():

                axis = axis.lower()

                if axis not in self.AXIS_MAP:
                    raise ValueError(
                        f"Invalid stiffness axis: {axis}"
                    )

                index = self.AXIS_MAP[axis]
                stiffness_vector[index] = value

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
        forces 예시:

        {"x": 40}

        또는

        {
            "x": 40,
            "z": -10,
            "a": 5,
        }
        """

        if mode not in self.MODE_MAP:
            raise ValueError(
                f"Invalid force mode: {mode}"
            )

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
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

            desired_force[index] = value
            direction[index] = 1

        print(
            f"[FORCE] ON "
            f"force={desired_force}, "
            f"direction={direction}, "
            f"mode={mode}, "
            f"reference={reference}",
            flush=True,
        )

        # 기준 좌표계 설정
        set_ref_coord(
            self.REFERENCE_MAP[reference]
        )

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
    # All OFF
    # =========================================================

    def all_off(self):

        print(
            "[FORCE CONTROL] ALL OFF",
            flush=True,
        )

        force_result = release_force()
        compliance_result = release_compliance_ctrl()

        print(
            f"[FORCE CONTROL] "
            f"force_off={force_result}, "
            f"compliance_off={compliance_result}",
            flush=True,
        )

        return force_result, compliance_result