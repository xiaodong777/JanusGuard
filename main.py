import psutil
import sqlite3
import configparser

class JanusGuardDataCore:
    def __init__(self):
        self.db_path = "janusguard_data.db"
        self.initialize_db()

    def initialize_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS process_data (
                id INTEGER PRIMARY KEY,
                pid INTEGER,
                process_name TEXT,
                local_address TEXT,
                remote_address TEXT,
                duplicates INTEGER DEFAULT 1
            )
            """)
            conn.commit()

    def collect_and_store_data(self):
        connections = []
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                for conn in proc.connections():
                    connections.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else 'N/A'
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for entry in connections:
                cursor.execute("""
                SELECT id FROM process_data WHERE pid=? AND process_name=? AND local_address=? AND remote_address=?
                """, (entry['pid'], entry['name'], entry['local_address'], entry['remote_address']))

                existing_entry = cursor.fetchone()
                if existing_entry:
                    cursor.execute("""
                    UPDATE process_data SET duplicates=duplicates+1 WHERE id=?
                    """, (existing_entry[0],))
                else:
                    cursor.execute("""
                    INSERT INTO process_data (pid, process_name, local_address, remote_address)
                    VALUES (?, ?, ?, ?)
                    """, (entry['pid'], entry['name'], entry['local_address'], entry['remote_address']))
            conn.commit()

if __name__ == "__main__":
    data_core = JanusGuardDataCore()

    config = configparser.ConfigParser()
    config.read('config.ini')
    interval = int(config['Settings']['CollectionInterval'])

    import time
    while True:
        data_core.collect_and_store_data()
        time.sleep(interval)
