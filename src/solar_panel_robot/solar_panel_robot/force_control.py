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


    def compliance_on(
        self,
        stiffness=None,
        time=0.0,
        reference="base",
    ):
        """Compliance Control 시작"""

        reference = reference.lower()

        if reference not in self.REFERENCE_MAP:
            raise ValueError(
                f"Invalid reference: {reference}"
            )


        stiffness_vector = [
            3000.0,
            3000.0,
            3000.0,
            200.0,
            200.0,
            200.0,
        ]


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
        """Compliance Control 종료"""

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


    def force_on(
        self,
        forces,
        time=0.0,
        mode="relative",
        reference="base",
    ):
        """Desired Force 적용"""

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
        """Desired Force 종료"""

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


    def all_off(self):
        """Force + Compliance Control 모두 종료"""

        print(
            "[FORCE CONTROL] ALL OFF",
            flush=True,
        )

        force_result = None
        compliance_result = None


        try:
            force_result = release_force()

        except Exception as e:

            print(
                f"[FORCE CONTROL] "
                f"force_off error={e}",
                flush=True,
            )


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