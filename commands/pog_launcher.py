import schedule
import time
import subprocess
import os
import signal
import sys
import logging
import time


class ProcessGroup:
    def __init__(self):
        self.ts3_process = None
        self.discord_process = None

    def kill_ts3(self):
        if self.ts3_process:
            logging.info("Sending soft exit signal to TS3 bot!")
            os.killpg(os.getpgid(self.ts3_process.pid), signal.SIGINT)
            self.ts3_process = None

    def kill_discord(self):
        if self.discord_process:
            logging.info("Sending soft exit signal to discord bot!")
            os.killpg(os.getpgid(self.discord_process.pid), signal.SIGINT)
            self.discord_process = None

    def restart_ts3(self):
        self.kill_ts3()
        logging.info("Starting TS3 bot!")
        time.sleep(5)
        self.ts3_process = subprocess.Popen(f"{os.getcwd()}/commands/ts3_bot_launcher.sh", shell=True, preexec_fn=os.setsid)

    def restart_discord(self):
        self.kill_discord()
        logging.info("Starting discord bot!")
        time.sleep(5)
        self.discord_process = subprocess.Popen(f"{os.getcwd()}/commands/discord_bot_launcher.sh", shell=True,
                                                preexec_fn=os.setsid)

    def clear_lobby(self):
        if self.discord_process:
            logging.info("Sending clean lobby signal!")
            os.killpg(os.getpgid(self.discord_process.pid), signal.SIGUSR1)

    def periodic_task(self):
        logging.info("======================================")
        logging.info("Periodic task triggered!")
        self.restart_ts3()
        # self.clear_lobby()
        logging.info("======================================")


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s | %(levelname)s %(message)s',
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S UTC")
    group = ProcessGroup()

    def stop_all(sig, frame):
        logging.info("======================================")
        logging.info("Signal received: Stopping all")
        group.kill_discord()
        group.kill_ts3()
        logging.info("Launcher exiting!")
        logging.info("======================================")
        time.sleep(2)
        sys.exit(0)

    def restart_1(sig, frame):
        logging.info("======================================")
        logging.info("Signal received: Restarting TS3 bot")
        group.restart_ts3()
        logging.info("======================================")

    def restart_2(sig, frame):
        logging.info("======================================")
        logging.info("Signal received: Restarting discord bot")
        group.restart_discord()
        logging.info("======================================")

    signal.signal(signal.SIGINT, stop_all)
    signal.signal(signal.SIGUSR1, restart_1)
    signal.signal(signal.SIGUSR2, restart_2)

    schedule.every().day.at("11:00").do(group.periodic_task)

    logging.info("======================================")
    logging.info("Launcher starting!")
    group.restart_ts3()
    group.restart_discord()
    logging.info("======================================")

    while True:
        schedule.run_pending()
        time.sleep(60)

