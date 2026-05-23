import sqlite3
import json
import os
from datetime import datetime
from .config import DB_NAME

class SniperDatabase:
    def __init__(self, db_path=DB_NAME):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initializes the database tables if they do not exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Table for currently held positions
        c.execute('''
            CREATE TABLE IF NOT EXISTS active_nets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                address TEXT,
                buy_price REAL,
                invested REAL,
                original_invested REAL,
                ath_price REAL,
                tp1_done BOOLEAN,
                tp2_done BOOLEAN,
                tp3_done BOOLEAN,
                tp4_done BOOLEAN,
                status TEXT,
                buy_timestamp REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Migrate: add buy_timestamp column if missing (for existing DBs)
        try:
            c.execute('ALTER TABLE active_nets ADD COLUMN buy_timestamp REAL')
        except Exception:
            pass
        
        # Table for completed trades (sold/rugpulled)
        c.execute('''
            CREATE TABLE IF NOT EXISTS past_nets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                address TEXT,
                buy_price REAL,
                invested REAL,
                original_invested REAL,
                ath_price REAL,
                tp1_done BOOLEAN,
                tp2_done BOOLEAN,
                tp3_done BOOLEAN,
                tp4_done BOOLEAN,
                status TEXT,
                buy_timestamp REAL,
                sell_price REAL,
                closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Migrate: add new columns to past_nets if missing
        for col_def in ['buy_timestamp REAL', 'sell_price REAL']:
            try:
                c.execute(f'ALTER TABLE past_nets ADD COLUMN {col_def}')
            except Exception:
                pass
        
        # Table for tracking wallet capital over time
        c.execute('''
            CREATE TABLE IF NOT EXISTS capital_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                capital REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        # Convert 1/0 back to boolean for tp states
        for key in ['tp1_done', 'tp2_done', 'tp3_done', 'tp4_done']:
            if key in d:
                d[key] = bool(d[key])
        return d

    def save_active_nets(self, nets: list):
        """Wipes and saves all active nets. In production you'd use UPSERT, but wipe is safer for sync here."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM active_nets')
        
        for net in nets:
            c.execute('''
                INSERT INTO active_nets (symbol, address, buy_price, invested, original_invested, ath_price, 
                                        tp1_done, tp2_done, tp3_done, tp4_done, status, buy_timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                net['symbol'], net['address'], net['buy_price'], net['invested'], 
                net.get('original_invested', net['invested']), net.get('ath_price', net['buy_price']),
                net.get('tp1_done', False), net.get('tp2_done', False), 
                net.get('tp3_done', False), net.get('tp4_done', False), net['status'],
                net.get('buy_timestamp', None)
            ))
            
        conn.commit()
        conn.close()

    def save_past_net(self, net: dict):
        """Appends a closed trade to history."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO past_nets (symbol, address, buy_price, invested, original_invested, ath_price, 
                                    tp1_done, tp2_done, tp3_done, tp4_done, status, buy_timestamp, sell_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            net['symbol'], net['address'], net['buy_price'], net.get('invested', 0), 
            net.get('original_invested', net.get('invested', 0)), net.get('ath_price', net['buy_price']),
            net.get('tp1_done', False), net.get('tp2_done', False), 
            net.get('tp3_done', False), net.get('tp4_done', False), net['status'],
            net.get('buy_timestamp', None), net.get('sell_price', None)
        ))
        conn.commit()
        conn.close()

    def add_capital_history(self, timestamp: float, capital: float):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT INTO capital_history (timestamp, capital) VALUES (?, ?)', (timestamp, capital))
        conn.commit()
        conn.close()

    def load_state(self):
        """Loads state on startup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = self.dict_factory
        c = conn.cursor()
        
        c.execute('SELECT * FROM active_nets')
        active_nets = c.fetchall()
        
        c.execute('SELECT * FROM past_nets ORDER BY closed_at DESC LIMIT 50')
        past_nets = c.fetchall()
        
        c.execute('SELECT timestamp, capital FROM capital_history ORDER BY timestamp ASC')
        history_rows = c.fetchall()
        capital_history = [[r['timestamp'], r['capital']] for r in history_rows]
        
        # If no history, assume 100
        capital = 100.0
        if capital_history:
            capital = capital_history[-1][1]
            
        conn.close()
        return active_nets, past_nets, capital_history, capital
