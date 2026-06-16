@echo off
echo =============================================
echo    MP3专辑封面下载器 - 发布包制作工具
echo =============================================
echo.

REM 创建发布目录
set RELEASE_DIR=release
echo 正在创建发布目录...
if exist %RELEASE_DIR% rd /s /q %RELEASE_DIR%
mkdir %RELEASE_DIR%

REM 复制主程序
echo 正在复制主程序...
copy dist\MP3专辑封面下载器.exe %RELEASE_DIR%\

REM 复制说明文档
echo 正在复制说明文档...
copy README.txt %RELEASE_DIR%\

REM 复制安装脚本
echo 正在复制安装脚本...
copy mp3pic_installer.bat %RELEASE_DIR%\安装.bat

REM 创建空的"示例"目录
echo 正在创建示例目录...
mkdir %RELEASE_DIR%\示例

echo.
echo 所有文件已准备就绪，位于 %RELEASE_DIR% 目录
echo 现在可以将此目录打包分发给其他用户
echo.
echo 按任意键退出...
pause > nul 