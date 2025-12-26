# -*- coding: utf-8 -*-
"""
automacao_sigaa.py
Versão FINAL OMNISCIENTE:
- Lê texto visível E texto oculto em ícones (title/alt).
- Tenta capturar volumes escondidos na coluna Status sem precisar clicar.
- Mantém a velocidade máxima.
"""

import re
import io
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# MAPA DE BIBLIOTECAS
BIBLIOTECA_MAP = {
    "BC - Biblioteca Central": "6", "BPHJ - Biblioteca Professor Hermano José": "800702",
    "CCA-AREIA - Biblioteca Setorial do CCA-AREIA": "19221", "CCAE - Biblioteca Setorial do CCAE": "325229",
    "CCEN - Biblioteca Setorial do CCEN": "27742", "CCHLA - Biblioteca Setorial do CCHLA": "14374",
    "CCHSA-BANANEIRAS - Biblioteca Setorial do CCHSA": "310140", "CCJ - Biblioteca Setorial do CCJ": "184760",
    "CCM - Biblioteca Setorial do CCM": "314284", "CCS - Biblioteca Setorial do CCS": "7",
    "CCSA - Biblioteca Setorial do CCSA": "314282", "CCTA - Biblioteca Setorial do CCTA": "364091",
    "CE - Biblioteca Setorial do CE": "322034", "CEAR - Biblioteca Setorial do CEAR": "396411",
    "CI - Biblioteca Setorial do CI": "485846", "CPT/ETS - Biblioteca Setorial da CPT/ETS": "1",
    "CT - Biblioteca Setorial do CT": "9763", "CTDR - Biblioteca Setorial do CTDR": "4889",
    "DCJ/CCJ-SANTARITA - Biblioteca Setorial do CCJ/DCJ-SANTA RITA": "753022", "HU - Biblioteca Setorial do HU": "327825",
    "NDIHR - Biblioteca Setorial do NDIHR": "336756"
}

def executar_automacao(titulo_livro, autor_desejado, volume_desejado, biblioteca_filtro, status):
    
    def reportar(msg):
        print(msg)
        if status:
            try: status.put(msg)
            except: pass

    reportar('Iniciando busca')
    driver = None
    dados_finais = []
    
    vol_target = None
    if volume_desejado and str(volume_desejado).strip().isdigit():
        vol_target = int(volume_desejado)
    
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 20)
        wait_long = WebDriverWait(driver, 30)

        url = 'https://sigaa.ufpb.br/sigaa/public/biblioteca/buscaPublicaAcervo.jsf'
        driver.get(url)

        # --- 1. PREENCHER BUSCA ---
        try:
            cb_titulo = wait.until(EC.presence_of_element_located((By.ID, 'formBuscaPublica:checkTitulo')))
            if not cb_titulo.is_selected(): cb_titulo.click()
            driver.find_element(By.XPATH, "//input[@id='formBuscaPublica:checkTitulo']/ancestor::tr[1]//input[@type='text']").send_keys(titulo_livro)
            
            if autor_desejado:
                cb_autor = driver.find_element(By.ID, 'formBuscaPublica:checkAutor')
                if not cb_autor.is_selected(): cb_autor.click()
                driver.find_element(By.XPATH, "//input[@id='formBuscaPublica:checkAutor']/ancestor::tr[1]//input[@type='text']").send_keys(autor_desejado)
            
            if biblioteca_filtro and biblioteca_filtro.upper() != 'TODAS AS BIBLIOTECAS':
                driver.find_element(By.ID, 'formBuscaPublica:checkBiblioteca').click()
                time.sleep(0.5)
                select_elem = driver.find_element(By.XPATH, "//th[normalize-space(text())='Biblioteca:']/following-sibling::td//select")
                Select(select_elem).select_by_value(BIBLIOTECA_MAP.get(biblioteca_filtro, ""))

            driver.find_element(By.ID, 'formBuscaPublica:botaoPesquisarPublicaMulti').click()
        except Exception as e:
            reportar(f"Erro ao preencher formulário: {e}"); raise

        # --- 2. LOOP DE PÁGINAS DA BUSCA ---
        pagina_atual = 1
        while True:
            reportar(f'Processando página {pagina_atual}...')
            try:
                wait_long.until(EC.presence_of_element_located((By.XPATH, "//table[@class='listagem']")))
            except:
                reportar("Fim da busca.")
                break

            linhas = driver.find_elements(By.XPATH, "//table[@class='listagem']/tbody/tr[contains(@class,'linha')][count(td)>=5]")
            indices_validos = [i for i in range(len(linhas))]

            if not indices_validos:
                reportar("Nenhum livro nesta página.")

            for idx in indices_validos:
                try:
                    # RE-BUSCA (Anti-Stale)
                    linhas_re = driver.find_elements(By.XPATH, "//table[@class='listagem']/tbody/tr[contains(@class,'linha')][count(td)>=5]")
                    if idx >= len(linhas_re): break
                    
                    linha = linhas_re[idx]
                    lupa = linha.find_element(By.CSS_SELECTOR, "a img[title*='visualizar']")
                    driver.execute_script("arguments[0].click()", lupa.find_element(By.XPATH, ".."))
                    
                    wait_long.until(EC.presence_of_element_located((By.XPATH, "//th[contains(text(),'Código de Barras')]")))
                    
                    # --- 3. LOOP DE EXEMPLARES ---
                    pagina_ex = 1
                    while True:
                        try:
                            xpath_trs = "//table[@class='visualizacao'][.//caption[contains(text(),'Exemplar')]]//tbody/tr"
                            qtd_linhas = len(driver.find_elements(By.XPATH, xpath_trs))
                        except: qtd_linhas = 0

                        biblioteca_atual = "Geral"
                        i_ex = 0

                        while i_ex < qtd_linhas:
                            try:
                                trs = driver.find_elements(By.XPATH, xpath_trs)
                                if i_ex >= len(trs): break
                                
                                tr = trs[i_ex]
                                cls = tr.get_attribute("class") or ""
                                texto_tr_principal = tr.text.strip()
                                
                                # Tenta pegar texto oculto em ícones (title ou alt)
                                # Isso ajuda se o status estiver em um ícone com hover
                                texto_oculto = ""
                                imagens = tr.find_elements(By.TAG_NAME, "img")
                                for img in imagens:
                                    title = img.get_attribute("title")
                                    alt = img.get_attribute("alt")
                                    if title: texto_oculto += " " + title
                                    if alt: texto_oculto += " " + alt
                                
                                # Cabeçalho de Biblioteca
                                if "biblioteca" in cls.lower():
                                    biblioteca_atual = texto_tr_principal
                                    i_ex += 1
                                    continue
                                
                                tds = tr.find_elements(By.TAG_NAME, "td")
                                if not tds:
                                    i_ex += 1; continue
                                
                                texto_col1 = tds[0].text.strip()
                                colecao = tds[1].text.strip() if len(tds) > 1 else "Indefinida"

                                # --- CHECAGEM 1: É CÓDIGO VÁLIDO? ---
                                if not re.search(r'^\d+[\/\-]\d+', texto_col1) or "Localização" in texto_col1:
                                    i_ex += 1
                                    continue
                                
                                # --- PEGAR INFORMAÇÃO DA PRÓXIMA LINHA ---
                                texto_localizacao_next = ""
                                if i_ex + 1 < len(trs):
                                    tr_next = trs[i_ex + 1]
                                    txt_next = tr_next.text.strip()
                                    if "Localização" in txt_next or "Tipo de Material" in txt_next:
                                        texto_localizacao_next = txt_next

                                # Texto Completo = Visível + Oculto (ícones) + Próxima Linha
                                texto_analise_total = (texto_tr_principal + " " + texto_oculto + " " + texto_localizacao_next).lower()

                                # --- FILTRO DE VOLUME MATEMÁTICO ---
                                aceitar_volume = True
                                if vol_target is not None:
                                    # Regex
                                    padrao_vol = r'\b(?:v|vol|volume|t|tom|tomo)\.?\s*(\d+)\b'
                                    matches = re.findall(padrao_vol, texto_analise_total)
                                    
                                    if matches:
                                        vol_str = matches[0]
                                        try:
                                            vol_num = int(vol_str)
                                            if vol_num != vol_target:
                                                aceitar_volume = False
                                        except: pass

                                if aceitar_volume:
                                    aceitar_bib = True
                                    if biblioteca_filtro and biblioteca_filtro != "TODAS AS BIBLIOTECAS":
                                        sigla = biblioteca_filtro.split()[0]
                                        if sigla not in colecao and sigla not in biblioteca_atual:
                                            aceitar_bib = False
                                    
                                    if aceitar_bib:
                                        dados_finais.append({
                                            "Coleção": colecao,
                                            "Código de Barras": texto_col1,
                                            "Biblioteca": biblioteca_atual
                                        })
                                        reportar(f"Coletado: {texto_col1}")

                                i_ex += 1 

                            except StaleElementReferenceException:
                                time.sleep(0.5)
                                continue 
                            except Exception:
                                i_ex += 1; continue

                        try:
                            prox = driver.find_element(By.XPATH, f"//a[contains(@class,'pagination') and text()='{pagina_ex + 1}']")
                            driver.execute_script("arguments[0].click()", prox)
                            time.sleep(1)
                            pagina_ex += 1
                        except: break

                    # Voltar
                    try:
                        driver.find_element(By.ID, "formDetalhesMateriaisPublico:voltarAhTelaDeBusca").click()
                        wait_long.until(EC.presence_of_element_located((By.CLASS_NAME, "listagem")))
                    except:
                        driver.back()
                        wait_long.until(EC.presence_of_element_located((By.CLASS_NAME, "listagem")))

                except Exception as e:
                    driver.back()
                    time.sleep(1)

            try:
                prox = driver.find_element(By.ID, "formBuscaPublica:botaoProximaPagina")
                if prox.tag_name == "a":
                    driver.execute_script("arguments[0].click()", prox)
                    pagina_atual += 1
                    time.sleep(1)
                else: break
            except: break

    except Exception as e:
        reportar(f"Erro fatal: {e}")
    finally:
        if driver: driver.quit()

    if dados_finais:
        reportar("Gerando Excel...")
        df = pd.DataFrame(dados_finais)
        df = df.sort_values(by=['Biblioteca', 'Coleção', 'Código de Barras'])
        
        exportacao = []
        total_geral = 0
        
        for (bib, col), grupo in df.groupby(['Biblioteca', 'Coleção']):
            qtd = len(grupo)
            total_geral += qtd
            titulo_grupo = f"{bib} ({col})"
            
            exportacao.append({"Estrutura": titulo_grupo, "Código de Barras": ""}) 
            for c in grupo['Código de Barras']:
                exportacao.append({"Estrutura": "", "Código de Barras": c})
            
            exportacao.append({"Estrutura": "", "Código de Barras": f"Subtotal: {qtd}"})
            exportacao.append({"Estrutura": "", "Código de Barras": ""})
        
        exportacao.append({"Estrutura": "TOTAL GERAL", "Código de Barras": total_geral})
        
        buffer = io.BytesIO()
        pd.DataFrame(exportacao).to_excel(buffer, index=False)
        return buffer.getvalue(), f"Relatorio_Final_{titulo_livro[:10].strip()}.xlsx"
    
    return None, None