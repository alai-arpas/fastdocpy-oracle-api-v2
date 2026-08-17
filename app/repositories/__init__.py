"""Query Oracle con bind variables, raggruppate per dominio.

A differenza del legacy (SQL costruito con f-string, valori della request
interpolati direttamente nel testo), qui i parametri passano sempre come
bind variables (`oracledb` accetta anche `datetime` Python legati a colonne
DATE/TIMESTAMP), eliminando il rischio di SQL injection.
"""
