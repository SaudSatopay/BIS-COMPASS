# Capture two screens of the BIS Compass demo from the running localhost.
# Uses Selenium-free direct CDP via Chrome's --remote-debugging-port if started
# with that flag, OR falls back to Add-Type screen capture of the active window.
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Capture-Screen($outPath) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
    $bmp.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Host "saved $outPath"
}

# Args: 1=output path
param([string]$Out = "screen.png")
Capture-Screen $Out
