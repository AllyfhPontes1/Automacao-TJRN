import pyautogui
import time

if botao:
    pyautogui.moveTo(botao, duration=1)
    pyautogui.click()
    print("Clique no botão 'Na unidade' realizado com sucesso!")
else:
    print(" Botão não encontrado. Tente ajustar o print ou o confidence.")


time.sleep(10)  