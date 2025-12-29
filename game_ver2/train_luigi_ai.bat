@echo off
REM Train Luigi RL AI for PVE mode
cd /d "%~dp0"

echo ========================================
echo Training Luigi AI for PVE Mode
echo ========================================
echo.

REM Activate conda environment
call conda activate mp_env

echo Starting training (this may take 5-10 minutes)...
echo.

cd game\rl_training
python train_luigi_pve.py --train --timesteps 50000

echo.
echo ========================================
echo Training complete!
echo ========================================
echo.
echo The trained model is saved as: luigi_pve_ai.zip
echo You can now play PVE mode with the trained Luigi AI.
echo.
pause
