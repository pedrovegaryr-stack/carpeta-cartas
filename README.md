# Carpeta de cartas Pokémon

Web estática: `index.html` + fotos en `img/` + stock editable en `stock.csv`.

## Cambiar precios o marcar cartas vendidas

Todo se hace en **`stock.csv`**, sin tocar `index.html`.

Cada línea es una carta:

```
id;carta;precio;cantidad
35;Mega Kangaskhan ex 182;60.00;1
```

- **Cambiar el precio:** edita la tercera columna (vale `2.50` o `2,50`).
- **Vendida / sin stock:** pon la cantidad a `0`. La carta sigue en la web, en gris, con el sello «Agotada», al final de la lista y fuera de los totales y de las descargas en PDF y Excel.
- **Vuelve a haber stock:** pon otra vez la cantidad.
- No cambies la columna `id`. La columna `carta` es solo para que sepas cuál es.

Desde GitHub: abre `stock.csv`, pulsa el lápiz (Edit), cambia lo que quieras y pulsa **Commit changes**. Vercel publica el cambio solo en menos de un minuto.

## Añadir cartas nuevas

Las cartas nuevas necesitan su foto y sus datos: pásale la lista a Claude y te devolverá los archivos actualizados.
