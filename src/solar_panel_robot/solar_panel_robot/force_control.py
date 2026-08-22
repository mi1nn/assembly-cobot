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

    def compliance_on(
        self,
        stiffness=(3000, 3000, 3000, 200, 200, 200),
        time=0.0,
        reference="base"
    ):
        print(
            f"[COMPLIANCE] ON "
            f"stiffness={stiffness}, "
            f"time={time}",
            flush=True
        )

        reference_map = {
        "base": DR_BASE,
        "tool": DR_TOOL,
        }

        if reference not in reference_map:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        set_ref_coord(
            reference_map[reference]
        )

        result = task_compliance_ctrl(
            stx=list(stiffness),
            time=time
        )

        print(
            f"[COMPLIANCE] result={result}",
            flush=True
        )

        return result


    def compliance_off(self):
        print(
            "[COMPLIANCE] OFF",
            flush=True
        )

        result = release_compliance_ctrl()

        print(
            f"[COMPLIANCE] OFF result={result}",
            flush=True
        )

        return result


    def force_on(
        self,
        desired_force=(0, 0, -10, 0, 0, 0),
        direction=(0, 0, 1, 0, 0, 0),
        time=0.0,
        mode="relative",
        reference="base"
    ):
        mode_map = {
            "relative": DR_FC_MOD_REL,
            "absolute": DR_FC_MOD_ABS,
        }

        reference_map = {
            "base": DR_BASE,
            "tool": DR_TOOL,
        }

        if mode not in mode_map:
            raise ValueError(
                f"Invalid force mode: {mode}"
            )

        if reference not in reference_map:
            raise ValueError(
                f"Invalid reference: {reference}"
            )

        print(
            f"[FORCE] ON "
            f"force={desired_force}, "
            f"direction={direction}, "
            f"mode={mode}, "
            f"reference={reference}",
            flush=True
        )

        # 목표 힘 설정
        force_result = set_desired_force(
            fd=list(desired_force),
            dir=list(direction),
            time=time,
            mod=mode_map[mode]
        )

        print(
            f"[FORCE] set_desired_force result={force_result}",
            flush=True
        )

        return force_result


    def force_off(self):
        print(
            "[FORCE] OFF",
            flush=True
        )

        result = release_force()

        print(
            f"[FORCE] OFF result={result}",
            flush=True
        )

        return result


    def all_off(self):
        print(
            "[FORCE CONTROL] ALL OFF",
            flush=True
        )

        force_result = release_force()
        compliance_result = release_compliance_ctrl()

        print(
            f"[FORCE CONTROL] "
            f"force_off={force_result}, "
            f"compliance_off={compliance_result}",
            flush=True
        )