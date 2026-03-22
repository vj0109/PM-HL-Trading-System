#!/usr/bin/env python3
"""
CLOSE ALL POSITIONS - Following Claude's instructions to start fresh
Cancel all HL and PM paper positions before rebuilding system
"""

import psycopg2
from datetime import datetime

def close_all_positions():
    print("🚨 CLOSING ALL POSITIONS - STARTING FRESH")
    print("=" * 50)
    
    conn = psycopg2.connect('postgresql://agentfloor:V1S2I3O4J@localhost:5432/agentfloor')
    cur = conn.cursor()
    
    # Close all open HL positions
    cur.execute("""
        UPDATE simple_hl_trades 
        SET status = 'CLOSED',
            exit_time = NOW(),
            exit_reason = 'MANUAL_CLOSE_REBUILD'
        WHERE status = 'OPEN'
    """)
    
    hl_closed = cur.rowcount
    
    # Close all open PM positions (set result to indicate manual close)
    cur.execute("""
        UPDATE polymarket_paper_trades
        SET result = 'MANUAL_CLOSE_REBUILD',
            resolved_at = NOW()
        WHERE result IS NULL OR result = ''
    """)
    
    pm_closed = cur.rowcount
    
    conn.commit()
    
    print(f"✅ CLOSED {hl_closed} HL positions")
    print(f"✅ CLOSED {pm_closed} PM positions") 
    print(f"📊 Total positions closed: {hl_closed + pm_closed}")
    print()
    print("🔄 READY TO IMPLEMENT CLAUDE'S PHASE 0 FOUNDATION")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    close_all_positions()