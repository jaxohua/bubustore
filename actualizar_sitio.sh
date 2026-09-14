#!/bin/bash

echo "=========================================="
echo "Iniciando actualización de la tienda..."
echo "=========================================="

# Agregar todos los cambios (nuevos precios, productos marcados como vendidos, etc)
git add .

# Hacer el commit con la fecha y hora actual
FECHA=$(date +"%Y-%m-%d %H:%M:%S")
git commit -m "Actualización de inventario y precios - $FECHA"

# Subir los cambios a GitHub
echo "Subiendo cambios a GitHub..."
git push

echo "=========================================="
echo "¡Actualización completada exitosamente!"
echo "Tus clientes verán los cambios en un par de minutos."
echo "=========================================="
