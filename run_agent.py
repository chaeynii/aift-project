from rt_kiwoom import *
from agent import *
from time_manager import TimeManager
from config_manager import ConfigManager
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    cm = ConfigManager('config/.config.template.xml')
    rt_kiwoom_ocx = RTKiwoom()
    agent = RTAgent(rt_kiwoom_ocx, config_manager=cm)
    if not agent.time_manager.is_today_open():
        agent.get_logger().warning("오늘은 장이 안열리는 날이라 종료됩니다.")
        sys.exit(0)
    elif not agent.time_manager.less_than_minutes_before_open(30):
        agent.get_logger().warning("8시 30분이전이기 때문에 프로그램 종료됩니다.")
        sys.exit(0)
    elif TimeManager.get_now() > agent.time_manager.when_to_close():
        agent.get_logger().warning("장이 종료되었기 때문에 프로그램 종료됩니다.")
        sys.exit(0)

    agent.get_logger().info('Start PreStage')
    agent.PreStage()
    agent.get_logger().info(agent.get_account_str())
    agent.get_logger().info('End PreStage')
    agent.get_logger().info('Start MainStage')

    agent.MainStage()
    agent.get_logger().info('End MainStage... EventLoop enters.')
    app.exec_()
