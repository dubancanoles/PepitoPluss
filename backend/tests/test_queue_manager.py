import multiprocessing

from app.crawler.queue_manager import GestorColaURLs


def intentar_encolar(gestor, barrera, resultados, lock_resultados):
    barrera.wait()  # fuerza a que los 20 procesos ataquen al mismo tiempo
    ok = gestor.encolar_si_nueva("https://mismo-sitio.com/pagina")
    with lock_resultados:
        resultados.append(ok)


def test_url_no_se_encola_dos_veces_con_20_procesos_simultaneos():
    """
    RF4: aunque 20 procesos intenten encolar la misma URL exactamente al
    mismo tiempo (como pasaria si varios workers la descubren desde
    paginas distintas), solo uno debe lograrlo.
    """
    manager = multiprocessing.Manager()
    gestor = GestorColaURLs(
        cola=manager.Queue(),
        vistas=manager.dict(),
        contadas_por_dominio=manager.dict(),
        lock=manager.Lock(),
    )
    
    resultados = manager.list()
    lock_resultados = manager.Lock()
    barrera = manager.Barrier(20)

    procesos = [
        multiprocessing.Process(target=intentar_encolar, args=(gestor, barrera, resultados, lock_resultados))
        for _ in range(20)
    ]
    for p in procesos:
        p.start()
    for p in procesos:
        p.join()

    resultados_list = list(resultados)
    assert resultados_list.count(True) == 1
    assert resultados_list.count(False) == 19


def test_urls_distintas_se_encolan_todas():
    manager = multiprocessing.Manager()
    gestor = GestorColaURLs(
        cola=manager.Queue(),
        vistas=manager.dict(),
        contadas_por_dominio=manager.dict(),
        lock=manager.Lock(),
    )
    urls = [f"https://ejemplo.com/pagina-{i}" for i in range(10)]

    for url in urls:
        assert gestor.encolar_si_nueva(url) is True

    obtenidas = []
    while not gestor.esta_vacia():
        obtenidas.append(gestor.obtener(timeout=0.5))

    assert sorted(obtenidas) == sorted(urls)
