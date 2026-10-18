"""Pruebas de sintetizar-polly.py. No llaman a AWS ni necesitan claves:  python -m unittest test_sintetizar_polly -v"""
import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('sp', os.path.join(AQUI, 'sintetizar-polly.py'))
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


class ClienteFalso:
    def __init__(self, mp3):
        self.llamadas = []
        self.mp3 = mp3

    def synthesize_speech(self, **kw):
        self.llamadas.append(kw)
        return {'AudioStream': io.BytesIO(self.mp3)}


def hacer_mp3(ruta, seg=1):
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', 'sine=frequency=400:duration=%d' % seg, '-ac', '1', ruta], check=True)


class Pruebas(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        for n, t in {1: 'Hola mundo.', 2: 'Segunda parte con texto.'}.items():
            open(os.path.join(self.d, 'parte-%02d.txt' % n), 'w', encoding='utf-8').write(t + '\n')
        open(os.path.join(self.d, 'parte-01-ssml.txt'), 'w', encoding='utf-8').write('<speak>Hola <break time="600ms"/> mundo.</speak>\n')
        self.mp3 = os.path.join(self.d, '_t.mp3')
        hacer_mp3(self.mp3)
        self.bytes = open(self.mp3, 'rb').read()
        self._uso = sp.AQUI
        self.addCleanup(shutil.rmtree, self.d)
        self.ruta_uso = os.path.join(sp.AQUI, '.uso-polly.json')
        self.uso_previo = open(self.ruta_uso, encoding='utf-8').read() if os.path.exists(self.ruta_uso) else None
        if self.uso_previo is not None:
            os.remove(self.ruta_uso)

    def tearDown(self):
        if os.path.exists(self.ruta_uso):
            os.remove(self.ruta_uso)
        if self.uso_previo is not None:
            open(self.ruta_uso, 'w', encoding='utf-8').write(self.uso_previo)

    def test_lee_partes_y_ssml(self):
        self.assertEqual(list(sp.leer_partes(self.d)), [1, 2])
        self.assertEqual(list(sp.leer_partes(self.d, ssml=True)), [1])

    def test_facturables_ignoran_etiquetas(self):
        self.assertEqual(sp.caracteres_facturables('<speak>Hola <break time="600ms"/> mundo.</speak>'), len('Hola  mundo.'))

    def test_cupo(self):
        sp.comprobar_cupo(0, 100)
        with self.assertRaises(sp.ErrorPolly):
            sp.comprobar_cupo(499_950, 100)
        sp.comprobar_cupo(499_950, 100, permitir_pago=True)
        avisos = []
        sp.comprobar_cupo(399_990, 100, aviso=avisos.append)
        self.assertEqual(len(avisos), 1)

    def test_solo_texto_no_usa_cliente(self):
        sal = []
        self.assertEqual(sp.principal([self.d, '--solo-texto'], salida=sal.append), 0)
        self.assertTrue(any('Hola mundo.' in s for s in sal))

    def test_genera_partes_con_parametros_correctos_y_une(self):
        cli = ClienteFalso(self.bytes)
        out = os.path.join(self.d, 'final.wav')
        sp.principal([self.d, '--salida', out], cliente=cli, salida=lambda *_: None)
        self.assertEqual(len(cli.llamadas), 2)
        k = cli.llamadas[0]
        self.assertEqual((k['VoiceId'], k['Engine'], k['LanguageCode'], k['OutputFormat'], k['TextType']), ('Raul', 'long-form', 'es-ES', 'mp3', 'text'))
        self.assertTrue(os.path.getsize(out) > 1000)
        self.assertTrue(os.path.exists(os.path.join(self.d, 'ajustes.txt')))
        self.assertEqual(sp.leer_uso(self.ruta_uso)[sp.mes_actual()], len('Hola mundo.') + len('Segunda parte con texto.'))

    def test_solo_una_parte_y_ssml(self):
        cli = ClienteFalso(self.bytes)
        sp.principal([self.d, '--solo', '1', '--ssml'], cliente=cli, salida=lambda *_: None)
        self.assertEqual(len(cli.llamadas), 1)
        self.assertEqual(cli.llamadas[0]['TextType'], 'ssml')

    def test_parte_demasiado_larga(self):
        open(os.path.join(self.d, 'parte-03.txt'), 'w', encoding='utf-8').write('x' * 3001)
        with self.assertRaises(sp.ErrorPolly):
            sp.principal([self.d, '--solo-texto'], salida=lambda *_: None)

    def test_sin_claves(self):
        previo = {k: os.environ.pop(k, None) for k in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY')}
        try:
            with self.assertRaises(sp.ErrorPolly):
                sp.crear_cliente()
        finally:
            for k, v in previo.items():
                if v is not None:
                    os.environ[k] = v

    def test_la_clave_no_se_imprime(self):
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'CLAVE-SECRETA-123'
        try:
            sal = []
            sp.principal([self.d, '--solo-texto'], salida=sal.append)
            self.assertFalse(any('CLAVE-SECRETA-123' in s for s in sal))
        finally:
            del os.environ['AWS_SECRET_ACCESS_KEY']


if __name__ == '__main__':
    unittest.main()
