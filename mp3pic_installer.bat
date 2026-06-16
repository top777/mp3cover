@echo off
echo =========================================
echo MP3专辑封面下载器安装程序
echo =========================================
echo.

REM 创建桌面快捷方式
echo 正在创建桌面快捷方式...
copy "MP3专辑封面下载器.exe" "%USERPROFILE%\Desktop\"
echo 桌面快捷方式创建完成！

REM 将应用添加到系统路径
echo 正在添加程序到系统路径...
setx PATH "%PATH%;%CD%" /M
echo 路径添加完成！

echo.
echo 安装成功！
echo 您可以从桌面直接启动"MP3专辑封面下载器.exe"，或者从任意位置通过命令行运行"MP3专辑封面下载器"命令。
echo.
echo 按任意键退出...
pause > nul 