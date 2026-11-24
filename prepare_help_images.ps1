$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$folder = Join-Path $PSScriptRoot 'help-images'
$gray = [System.Drawing.Imaging.ColorMatrix]::new()
# Average the three ClearType channels so their colored edges become gray coverage.
$channel = [single](1.0 / 3)
$gray.Matrix00 = $gray.Matrix01 = $gray.Matrix02 = $channel
$gray.Matrix10 = $gray.Matrix11 = $gray.Matrix12 = $channel
$gray.Matrix20 = $gray.Matrix21 = $gray.Matrix22 = $channel

foreach ($language in 'en', 'ru') {
    $source = [System.Drawing.Bitmap]::new((Join-Path $folder "vita3k-$language.png"))
    try {
        $width = [int][Math]::Ceiling($source.Width * 2.0 / 3)
        $height = [int][Math]::Ceiling($source.Height * 2.0 / 3)
        $preview = [System.Drawing.Bitmap]::new($width, $height, [System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
        try {
            $graphics = [System.Drawing.Graphics]::FromImage($preview)
            $attributes = [System.Drawing.Imaging.ImageAttributes]::new()
            try {
                $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
                $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::Half
                $attributes.SetColorMatrix($gray)
                $attributes.SetWrapMode([System.Drawing.Drawing2D.WrapMode]::TileFlipXY)
                $bounds = [System.Drawing.Rectangle]::new(0, 0, $width, $height)
                $graphics.DrawImage($source, $bounds, 0, 0, $source.Width, $source.Height,
                    [System.Drawing.GraphicsUnit]::Pixel, $attributes)
            } finally {
                $attributes.Dispose()
                $graphics.Dispose()
            }
            $preview.Save((Join-Path $folder "vita3k-$language-inline.png"), [System.Drawing.Imaging.ImageFormat]::Png)
        } finally {
            $preview.Dispose()
        }
    } finally {
        $source.Dispose()
    }
}
