param([string]$root = (Get-Location).Path, [int]$port = 8731)
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")
$listener.Start()
Write-Output "serveur demarre sur http://localhost:$port/"
while ($listener.IsListening) {
  try {
    $ctx = $listener.GetContext()
    $rel = [System.Uri]::UnescapeDataString($ctx.Request.Url.LocalPath).TrimStart('/')
    $file = Join-Path $root $rel
    if ((Test-Path $file) -and -not (Get-Item $file).PSIsContainer) {
      $bytes = [System.IO.File]::ReadAllBytes($file)
      $ext = [System.IO.Path]::GetExtension($file).ToLower()
      $ct = "application/octet-stream"
      if ($ext -eq ".html") { $ct = "text/html; charset=utf-8" }
      elseif ($ext -eq ".pdf") { $ct = "application/pdf" }
      elseif ($ext -eq ".js") { $ct = "application/javascript" }
      elseif ($ext -eq ".png") { $ct = "image/png" }
      $ctx.Response.ContentType = $ct
      $ctx.Response.ContentLength64 = $bytes.Length
      $ctx.Response.OutputStream.Write($bytes, 0, $bytes.Length)
    } else {
      $ctx.Response.StatusCode = 404
    }
    $ctx.Response.Close()
  } catch { }
}
