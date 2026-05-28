@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion :: 啟用延遲變數擴展

:: 設定 Inkscape 執行檔的路徑
:: 如果您已將 Inkscape 加入到 PATH 環境變數，則可以將此變數設定為 "inkscape.com"
:: 否則，請替換成您實際的 Inkscape 執行檔路徑，例如 "C:\Program Files\Inkscape\bin\inkscape.com"
set "InkscapePath=inkscape.com"

:: 設定要處理的 SVG 檔案所在目錄
:: %~dp0 代表批次檔本身所在的目錄
set "SourceDirectory=%~dp0"
:: 確保 SourceDirectory 路徑末尾沒有反斜線，後面會手動添加
if "%SourceDirectory:~-1%"=="\" set "SourceDirectory=%SourceDirectory:~0,-1%"

:: 設定轉換後 PNG 檔案的輸出目錄
:: 這裡將輸出到與 SVG 檔案相同的目錄，您可以自行修改
set "OutputDirectory=%SourceDirectory%"
:: 確保 OutputDirectory 路徑末尾沒有反斜線，後面會手動添加
if "%OutputDirectory:~-1%"=="\" set "OutputDirectory=%OutputDirectory:~0,-1%"

:: 設定 PNG 輸出圖片的寬度和高度 (像素)
set "Width=128"
set "Height=128"

echo.
echo --- 開始 SVG 轉換為 PNG ---
echo.
echo 掃描目錄: !SourceDirectory!
echo 輸出尺寸: !Width!x!Height! 像素
echo.

:: 檢查 Inkscape 執行檔是否存在
where !InkscapePath! >nul 2>nul
if !errorlevel! neq 0 (
    echo 錯誤：找不到 Inkscape 執行檔。
    echo 請確認 Inkscape 已安裝，且其路徑已加入到 PATH 環境變數，或正確設定 InkscapePath 變數。
    echo 當前 InkscapePath: "!InkscapePath!"
    goto :eof
)

:: 遍歷指定目錄下的所有 .svg 檔案
for %%f in ("!SourceDirectory!\*.svg") do (
    :: 在迴圈內部使用 !變數名! 來確保變數的即時更新
    set "SvgFilePath=%%f"
    set "FileNameWithoutExtension=%%~nf"
    
    :: 組合輸出 PNG 檔案路徑，確保只有一個反斜線
    set "OutputPngPath=!OutputDirectory!\!FileNameWithoutExtension!.png"

    echo 轉換中: %%~nxf --> !FileNameWithoutExtension!.png

    :: 執行 Inkscape 命令進行轉換
    start /wait "" "!InkscapePath!" --export-filename="!OutputPngPath!" --export-type="png" --export-width=!Width! --export-height=!Height! --export-area-page "!SvgFilePath!"
    
    if !errorlevel! equ 0 (
        echo   成功轉換: !OutputPngPath!
    ) else (
        echo   轉換 %%~nxf 時發生錯誤！
    )
)

echo.
echo --- SVG 轉 PNG 轉換完成 ---
echo.

pause