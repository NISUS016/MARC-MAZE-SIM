"""view_3d.py — Ursina 3D view (best effort). Same Simulator underneath.

Scene: grey floor, white wall boxes (h=1) added on discovery,
orange robot box + heading nub, green goal floor, fixed isometric camera.
No physics, no smoothing — robot teleports per step.
Maze size (16..32) is read from sim.true; camera scales to fit.
"""


def run_3d(sim):
    from ursina import Ursina, Entity, Vec3, color, camera, time as utime

    W, H = sim.true.w, sim.true.h
    app = Ursina()
    CELL = 1.0

    def world(x, y):
        return Vec3(x * CELL + CELL / 2, 0, -(y * CELL + CELL / 2))

    floor_ents = {}
    for y in range(H):
        for x in range(W):
            c = color.light_gray if (x, y) not in sim.goals else color.green
            e = Entity(model="cube", color=c, scale=(CELL * 0.98, 0.1, CELL * 0.98),
                       position=world(x, y) + Vec3(0, -0.05, 0))
            floor_ents[(x, y)] = e

    wall_ents = []

    def sync_walls():
        for e in wall_ents:
            e.disable()
        wall_ents.clear()
        for y in range(H):
            for x in range(W):
                if (x, y) not in sim.explored:
                    continue
                p = world(x, y)
                if sim.known.has_wall(x, y, "N"):
                    wall_ents.append(Entity(model="cube", color=color.white,
                        scale=(CELL, 1, 0.1), position=p + Vec3(0, 0.5, -CELL / 2)))
                if sim.known.has_wall(x, y, "S"):
                    wall_ents.append(Entity(model="cube", color=color.white,
                        scale=(CELL, 1, 0.1), position=p + Vec3(0, 0.5, CELL / 2)))
                if sim.known.has_wall(x, y, "E"):
                    wall_ents.append(Entity(model="cube", color=color.white,
                        scale=(0.1, 1, CELL), position=p + Vec3(CELL / 2, 0.5, 0)))
                if sim.known.has_wall(x, y, "W"):
                    wall_ents.append(Entity(model="cube", color=color.white,
                        scale=(0.1, 1, CELL), position=p + Vec3(-CELL / 2, 0.5, 0)))

    robot_ent = Entity(model="cube", color=color.orange, scale=(0.7, 0.5, 0.7))
    nose = Entity(model="cube", color=color.red, scale=(0.2, 0.55, 0.2), parent=robot_ent)

    def sync_robot():
        p = world(*sim.pos)
        robot_ent.position = p + Vec3(0, 0.3, 0)
        off = {"N": (0, 0, -0.4), "S": (0, 0, 0.4),
               "E": (0.4, 0, 0), "W": (-0.4, 0, 0)}[sim.robot.heading]
        nose.position = Vec3(*off)

    def refresh():
        for (x, y), e in floor_ents.items():
            if (x, y) in sim.goals:
                e.color = color.green
            elif (x, y) in sim.explored:
                e.color = color.white
        if sim.optimal_path:
            for x, y in sim.optimal_path:
                floor_ents[(x, y)].color = color.lime
        sync_walls()
        sync_robot()

    refresh()
    # Fixed isometric camera above maze center (scales with maze size).
    cam_h = max(20.0, W * 1.25)
    camera.position = Vec3(W / 2, cam_h, -H / 2 - cam_h * 0.6)
    camera.look_at(Vec3(W / 2, 0, -H / 2))

    auto = {"on": True, "t": 0.0}

    def update():
        if auto["on"] and sim.phase not in ("OPTIMIZE", "DONE"):
            auto["t"] += utime.dt
            if auto["t"] > 0.15:
                auto["t"] = 0.0
                sim.step()
                refresh()

    def input(key):
        if key == "space":
            sim.step()
            refresh()
        elif key == "r":
            auto["on"] = not auto["on"]
        elif key == "s":
            sim.finish_exploration()
            refresh()
        elif key == "escape":
            app.destroy()

    app.update = update
    app.input = input
    app.run()
