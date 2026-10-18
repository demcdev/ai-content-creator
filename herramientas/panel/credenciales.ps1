# Guarda, lee y borra secretos en el Administrador de credenciales de Windows.
# Quedan cifrados con tu cuenta de Windows (DPAPI): no están en texto plano en el registro, ni en un archivo, ni en el historial
# de PowerShell. Solo se usa la API nativa de Windows (advapi32): no se instala ni se descarga nada.
# Se usa con «. .\credenciales.ps1» (desde iniciar-panel.ps1). Nunca imprime un valor.

if (-not ('CredencialesCanal' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class CredencialesCanal {
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct CREDENTIAL {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CredWrite(ref CREDENTIAL credential, int flags);
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CredRead(string target, int type, int flags, out IntPtr credential);
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CredDelete(string target, int type, int flags);
    [DllImport("advapi32.dll")]
    static extern void CredFree(IntPtr buffer);

    public static void Guardar(string target, string usuario, string secreto) {
        byte[] bytes = Encoding.Unicode.GetBytes(secreto);
        IntPtr blob = Marshal.AllocHGlobal(bytes.Length);
        try {
            Marshal.Copy(bytes, 0, blob, bytes.Length);
            CREDENTIAL c = new CREDENTIAL();
            c.Type = 1;                       // genérica
            c.TargetName = target;
            c.UserName = usuario;
            c.CredentialBlob = blob;
            c.CredentialBlobSize = bytes.Length;
            c.Persist = 2;                    // solo este equipo y esta cuenta
            if (!CredWrite(ref c, 0)) throw new System.ComponentModel.Win32Exception(Marshal.GetLastWin32Error());
        } finally {
            Marshal.FreeHGlobal(blob);
            Array.Clear(bytes, 0, bytes.Length);
        }
    }

    public static string Leer(string target) {
        IntPtr p;
        if (!CredRead(target, 1, 0, out p)) return null;
        try {
            CREDENTIAL c = (CREDENTIAL)Marshal.PtrToStructure(p, typeof(CREDENTIAL));
            if (c.CredentialBlobSize == 0) return "";
            byte[] bytes = new byte[c.CredentialBlobSize];
            Marshal.Copy(c.CredentialBlob, bytes, 0, c.CredentialBlobSize);
            return Encoding.Unicode.GetString(bytes);
        } finally {
            CredFree(p);
        }
    }

    public static bool Borrar(string target) {
        return CredDelete(target, 1, 0);
    }
}
'@
}

function Guardar-Secreto([string]$Prefijo, [string]$Nombre, [string]$Valor) { [CredencialesCanal]::Guardar("$Prefijo/$Nombre", $Nombre, $Valor) }
function Leer-Secreto([string]$Prefijo, [string]$Nombre) { [CredencialesCanal]::Leer("$Prefijo/$Nombre") }
function Borrar-Secreto([string]$Prefijo, [string]$Nombre) { [CredencialesCanal]::Borrar("$Prefijo/$Nombre") }
