from threading import Thread

from Config import run_time
from booking_thread import booking
from funct import get_current_time, waiting_until

# 这样线程不安全，不过懒得管了
tasks_data = []


def write_to_file():
    ps_list = ["lsx", "jht", "wcc", "cyl", "fyq"]
    with open("BookingTaskList/516.txt", "w") as btl:
        j = 0
        k = 0
        for i in tasks_data:
            k += i[2]
        for i in tasks_data:
            for _ in range(i[2]):
                btl.write(f"{ps_list[j]} {0 if i[0]==1 else ''}{i[0] + 8}:00-{i[0] + 9}:00 {i[1]}")
                j += 1
                if j < k:
                    btl.write("\n")
    tasks_data.clear()


def task_allocation():
    rt = []
    campus_list = ["516", "1100"]
    sqn = 1
    sph = {"remaining_ready": 0, "activate_num": 0}
    for sct in campus_list:
        with open(f"BookingTaskList/{sct}.txt", "r") as btl:
            for task in btl.readlines():
                task_info = task.split()
                rt.append(({
                               "person": task_info[0],
                               "time_slot": task_info[1],
                               "venue": int(task_info[2]),
                               "campus": sct,
                               "task_sequence": sqn,
                               "semaphore": sph
                           },))
                sqn += 1
    sph["remaining_ready"] = sqn - 1
    return rt


def perform_tasks():
    while True:
        # waiting_until((0, 5, 0))
        waiting_until((18, 42, 0))
        write_to_file()
        print(f"[{get_current_time()}]订场任务已生成")
        waiting_until(run_time)
        print(f"[{get_current_time()}]订场即将开始")
        tasklist = task_allocation()
        for i in tasklist:
            Thread(target=booking, args=i).start()
            # 上一个线程浏览器启动后，下一个线程的浏览器才启动
            while i[0]["task_sequence"] > i[0]["semaphore"]["activate_num"]:
                pass
        with open("BookingTaskList/516.txt", "w"):
            pass  # 清空BookingTaskList