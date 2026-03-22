#!/bin/bash
# Setup Daily Automated Assessment Cron Job
# Target: 5-10 predictions per day over 30 days

echo "🚀 SETTING UP DAILY AUTOMATED ASSESSMENT"

# Create cron job that runs twice daily (8 AM and 8 PM UTC)
CRON_SCRIPT="/home/vj/PM-HL-Trading-System/src/month1/automated_daily_process.py"
LOG_DIR="/home/vj/PM-HL-Trading-System/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create cron entry
CRON_ENTRY_1="0 8 * * * cd /home/vj/PM-HL-Trading-System/src/month1 && python3 automated_daily_process.py >> $LOG_DIR/daily_cron.log 2>&1"
CRON_ENTRY_2="0 20 * * * cd /home/vj/PM-HL-Trading-System/src/month1 && python3 automated_daily_process.py >> $LOG_DIR/daily_cron.log 2>&1"

# Add to crontab
echo "📅 Adding cron jobs:"
echo "   - 8:00 AM UTC daily assessment"
echo "   - 8:00 PM UTC additional assessment (if quota not met)"

# Check if cron entries already exist
if crontab -l 2>/dev/null | grep -q "automated_daily_process.py"; then
    echo "✅ Cron jobs already exist"
else
    # Add cron jobs
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY_1"; echo "$CRON_ENTRY_2") | crontab -
    echo "✅ Cron jobs added successfully"
fi

# Verify cron jobs
echo -e "\n📊 CURRENT CRONTAB:"
crontab -l | grep -E "(automated_daily|#)" || echo "No relevant entries found"

echo -e "\n🎯 DAILY PROCESS SUMMARY:"
echo "   Target: 7 predictions per day"  
echo "   Schedule: 8 AM and 8 PM UTC"
echo "   30-day goal: 210+ predictions"
echo "   Combined with 800 historical = 1,000+ total predictions"

echo -e "\n✅ AUTOMATION SETUP COMPLETE!"
echo "Daily assessments will run automatically starting tomorrow."
echo "Monitor logs at: $LOG_DIR/daily_cron.log"