# Enciende el servidor del panel con las claves de voz guardadas en el Administrador de credenciales de Windows.
#
#   iniciar-panel.cmd                  # carga las claves guardadas y enciende el servidor (doble clic o desde una terminal)
#   iniciar-panel.cmd -Configurar      # pide cada clave (oculta mientras escribes) y la guarda cifrada con tu cuenta
#   iniciar-panel.cmd -Olvidar         # borra las claves guardadas
#   iniciar-panel.cmd -SoloComprobar   # dice cuáles hay (solo nombres) y no enciende nada
#
# Las claves se leen solo para ESTA ventana: viven en su memoria y se van al cerrarla. No se escriben en archivos, no quedan
# en variables de entorno permanentes y nunca se imprimen. Los nombres salen de «claves_env» en herramientas/voz/voces.json.

param(
    [switch]$Configurar,
    [switch]$Olvidar,
    [switch]$SoloComprobar,
    [int]$Puerto = 8765,
    [string]$Prefijo = 'CanalYoutube'
)
$ErrorActionPreference = 'Stop'
$aqui = Split-Path -Parent $MyInvocation.MyCommand.Path
$raiz = (Resolve-Path (Join-Path $aqui '..\..')).Path
. (Join-Path $aqui 'credenciales.ps1')

$voces = (Get-Content -Raw -Encoding UTF8 (Join-Path $raiz 'herramientas\voz\voces.json') | ConvertFrom-Json).voces
$nombres = @($voces | ForEach-Object { $_.claves_env } | Where-Object { $_ } | Select-Object -Unique)
if ($nombres.Count -eq 0) { Write-Host 'voces.json no declara «claves_env»: no hay nada que guardar.'; exit 1 }

function Quien-Usa([string]$nombre) { ($voces | Where-Object { $_.claves_env -contains $nombre } | ForEach-Object { $_.id }) -join ', ' }

if ($Olvidar) {
    foreach ($n in $nombres) {
        $quitada = Borrar-Secreto $Prefijo $n
        Write-Host ('{0,-24} {1}' -f $n, $(if ($quitada) { 'borrada' } else { 'no estaba guardada' }))
    }
    exit 0
}

if ($Configurar) {
    Write-Host 'Escribe cada clave (no se ve mientras escribes). Enter vacío = conservar la que ya está guardada.'
    Write-Host 'Nunca pegues estas claves en el chat.'
    foreach ($n in $nombres) {
        $hay = $null -ne (Leer-Secreto $Prefijo $n)
        $etiqueta = '{0} [{1}] ({2})' -f $n, $(if ($hay) { 'guardada' } else { 'sin guardar' }), (Quien-Usa $n)
        if ($n -like '*REGION*') {      # la región no es un secreto: se ve al escribir
            $valor = Read-Host $etiqueta
        } else {
            $seguro = Read-Host -AsSecureString $etiqueta
            $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seguro)
            try { $valor = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
            finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
        }
        if ([string]::IsNullOrEmpty($valor)) { Write-Host '  se conserva'; continue }
        Guardar-Secreto $Prefijo $n $valor
        $valor = $null
        Write-Host '  guardada (cifrada con tu cuenta de Windows)'
    }
    Write-Host ''
}

$faltan = @()
foreach ($n in $nombres) {
    $v = Leer-Secreto $Prefijo $n
    if ($null -ne $v -and $v -ne '') {
        [Environment]::SetEnvironmentVariable($n, $v, 'Process')     # solo este proceso y sus hijos (el servidor)
        $v = $null
        Write-Host ('  ✓ {0,-24} ({1})' -f $n, (Quien-Usa $n))
    } else {
        $faltan += $n
        Write-Host ('  · {0,-24} sin guardar ({1})' -f $n, (Quien-Usa $n))
    }
}
if ($faltan.Count -gt 0) {
    Write-Host ''
    Write-Host 'Faltan claves: los pasos de voz que las usen quedarán bloqueados en el panel. Guárdalas con:  iniciar-panel.cmd -Configurar'
}
if ($SoloComprobar) { exit 0 }

try {
    $cliente = New-Object Net.Sockets.TcpClient
    $cliente.Connect('127.0.0.1', $Puerto)
    $cliente.Close()
    Write-Host ''
    Write-Host ('El puerto {0} ya está en uso: probablemente ya hay un servidor del panel encendido. Ciérralo antes y vuelve a ejecutar esto.' -f $Puerto)
    exit 1
} catch { }

Write-Host ''
Set-Location $raiz
& python 'herramientas/panel/servidor.py' --puerto $Puerto
