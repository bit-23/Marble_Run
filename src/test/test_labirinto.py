"""Testes da geracao procedural. Rodar na pasta src:  python -m unittest discover test"""
import os
import random
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jogo import gerar_labirinto, _distancias  # noqa: E402


class TesteLabirinto(unittest.TestCase):
    def test_sempre_tem_solucao(self):
        for semente in range(200):
            grade, entrada, saida, dist = gerar_labirinto(12, 8, random.Random(semente))
            self.assertIn(saida, _distancias(grade, entrada))
            self.assertGreater(dist, 0)

    def test_mesma_semente_gera_mesmo_labirinto(self):
        a = gerar_labirinto(10, 7, random.Random(42))
        b = gerar_labirinto(10, 7, random.Random(42))
        self.assertEqual(a, b)

    def test_sementes_diferentes_geram_labirintos_diferentes(self):
        a = gerar_labirinto(10, 7, random.Random(1))[0]
        b = gerar_labirinto(10, 7, random.Random(2))[0]
        self.assertNotEqual(a, b)

    def test_borda_e_toda_parede(self):
        grade = gerar_labirinto(10, 7, random.Random(3))[0]
        self.assertTrue(all(grade[0]) and all(grade[-1]))
        self.assertTrue(all(l[0] == 1 and l[-1] == 1 for l in grade))


if __name__ == "__main__":
    unittest.main()