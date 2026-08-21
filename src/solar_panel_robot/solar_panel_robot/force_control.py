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
        time=0.0
    ):

        print(
            f"[COMPLIANCE] ON "
            f"stiffness={stiffness}, "
            f"time={time}",
            flush=True
        )

        task_compliance_ctrl(
            stx=list(stiffness),
            time=time
        )


    def compliance_off(self):

        print("[COMPLIANCE] OFF", flush=True)

        release_compliance_ctrl()


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

        set_ref_coord(
            reference_map[reference]
        )

        set_desired_force(
            fd=list(desired_force),
            dir=list(direction),
            time=time,
            mod=mode_map[mode]
        )


    def force_off(self):

        print("[FORCE] OFF", flush=True)

        release_force()


    def all_off(self):

        print("[FORCE CONTROL] ALL OFF", flush=True)

        release_force()
        release_compliance_ctrl()