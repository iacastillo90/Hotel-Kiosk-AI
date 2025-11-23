#!/usr/bin/env python3
"""
generate_hotel_documents.py - Generador de Documentos Fuente

Este script GENERA los archivos de texto que serán leídos por ingest.py.
NO carga directamente a la base de datos (respeta arquitectura de una sola fuente).

Flujo correcto:
    1. python generate_hotel_documents.py  → Crea archivos .txt
    2. python ingest.py                    → Lee archivos y carga a ChromaDB
    3. python main.py                      → Usa la base de datos

Ventajas:
    - El hotel puede editar archivos .txt sin tocar código
    - ingest.py es la ÚNICA fuente de verdad para cargar datos
    - Escalable: puedes añadir PDFs, Excel, Word junto a los .txt
"""

import os
from pathlib import Path
from datetime import datetime


# ==============================================================================
# INFORMACIÓN DEL HOTEL PARADISE RESORT
# ==============================================================================

HOTEL_INFO = {
    # ==========================================================================
    # 1. INFORMACIÓN BÁSICA DEL HOTEL
    # ==========================================================================
    "info_basica": [
        "Hotel Paradise Resort es un hotel 5 estrellas ubicado en la Riviera Maya, México, frente a la playa de Tulum.",
        "El hotel cuenta con 280 habitaciones distribuidas en 4 edificios principales con vista al mar Caribe.",
        "Dirección completa: Carretera Tulum-Boca Paila Km 7.5, Zona Hotelera, 77780 Tulum, Quintana Roo, México.",
        "Teléfono principal: +52 (984) 871-2500. WhatsApp: +52 (984) 871-2501. Email: info@paradiseresort.mx",
        "Recepción disponible 24 horas al día, 7 días a la semana. Check-in: 15:00 hrs. Check-out: 12:00 hrs.",
        "El hotel fue inaugurado en 2018 y renovado completamente en 2023 con certificación LEED Gold por sustentabilidad.",
        "Contamos con personal multilingüe: español, inglés, francés, alemán y mandarín.",
    ],
    
    # ==========================================================================
    # 2. HABITACIONES Y TARIFAS
    # ==========================================================================
    "habitaciones": [
        "Habitación Estándar Vista Jardín: 35m², cama king size o dos camas queen, balcón privado, aire acondicionado, TV 55' smart, minibar. Precio: $180 USD/noche.",
        "Habitación Superior Vista Mar: 40m², cama king size, balcón amplio con vista al mar, jacuzzi en terraza, cafetera Nespresso. Precio: $250 USD/noche.",
        "Junior Suite Frente al Mar: 55m², sala de estar separada, cama king size, terraza privada con hamaca, bata y pantuflas de cortesía. Precio: $350 USD/noche.",
        "Suite Presidencial: 120m², 2 habitaciones, 2 baños completos, sala y comedor, terraza con piscina privada, mayordomo 24h. Precio: $800 USD/noche.",
        "Villa con Alberca Privada: 150m², 3 habitaciones, cocina completa, alberca infinity de 35m², jardín privado, chef a solicitud. Precio: $1200 USD/noche.",
        "Todas las habitaciones incluyen: WiFi de alta velocidad (fibra óptica 200 Mbps), caja fuerte digital, secadora de cabello Dyson, amenidades de baño orgánicas.",
        "Servicio de habitaciones disponible 24/7 sin cargo adicional. Cambio de toallas diario y limpieza completa cada dos días (servicio ecológico).",
        "Check-in anticipado disponible desde las 12:00 hrs con cargo de $50 USD. Check-out tardío hasta las 15:00 hrs con cargo de $60 USD (sujeto a disponibilidad).",
        "Habitaciones accesibles para personas con movilidad reducida disponibles en planta baja con rampas y baños adaptados.",
    ],
    
    # ==========================================================================
    # 3. RESTAURANTES Y BARES
    # ==========================================================================
    "restaurantes": [
        "Restaurante 'Mar y Tierra': Cocina internacional tipo buffet. Horario: desayuno 6:30-11:00, comida 13:00-16:00, cena 18:30-22:00. Dress code: casual.",
        "Restaurante 'Sakura': Cocina japonesa auténtica, chef de Osaka. Sushi, sashimi, teppanyaki. Horario: 18:00-23:00. Reservación obligatoria. Dress code: elegante casual.",
        "Restaurante 'La Trattoria': Cocina italiana gourmet, pasta fresca hecha en casa. Horario: 18:00-22:30. Reservación recomendada. Terraza romántica disponible.",
        "Restaurante 'Sabor Mexicano': Auténtica cocina mexicana regional, chef especializado en Oaxaca y Puebla. Horario: 13:00-22:00. Menú degustación de 7 tiempos disponible.",
        "Snack Bar 'Playa Azul': Junto a la alberca principal. Hamburguesas, tacos, ensaladas, smoothies. Horario: 11:00-18:00. Servicio directo a camastros.",
        "Bar 'Sunset Lounge': Bar principal con terraza, más de 200 etiquetas de tequila y mezcal. Mixología de autor. Horario: 16:00-02:00. Happy hour 17:00-19:00.",
        "Bar 'Aqua': Bar en la alberca infinity, cócteles tropicales y cervezas artesanales. Horario: 10:00-19:00. No se permite fumar.",
        "Servicio de Room Service 24/7 con menú completo. Delivery sin cargo adicional. Opción de cena romántica en habitación con decoración incluida ($80 USD).",
        "Desayuno continental incluido para todas las habitaciones. Upgrade a desayuno buffet premium: $25 USD por persona.",
        "Opciones vegetarianas, veganas, sin gluten y kosher disponibles en todos los restaurantes. Informar alergias alimentarias al hacer reservación.",
    ],
    
    # ==========================================================================
    # 4. PISCINAS Y PLAYA
    # ==========================================================================
    "piscinas_playa": [
        "Alberca Infinity Principal: 800m², temperatura 28°C, profundidad 1.20m-2.50m, vista panorámica al mar. Horario: 7:00-20:00.",
        "Alberca para Niños: 150m², juegos acuáticos, profundidad 0.40m-0.80m, área techada. Salvavidas permanente.",
        "Alberca Exclusiva Adultos: 400m², área silenciosa, jacuzzi integrado (6 plazas), servicio de toallas premium. Solo mayores de 18 años.",
        "Playa Privada: 300 metros lineales de arena blanca, marea tranquila ideal para snorkel. Palapas y camastros sin costo adicional.",
        "Servicio de playa incluye: toallas de playa ilimitadas (cambio sin límite), protector solar biodegradable de cortesía, agua fresca en dispensadores.",
        "Deportes acuáticos disponibles: kayaks (gratis), paddleboard (gratis), snorkel con equipo ($15 USD/día), motos acuáticas ($80 USD/30min).",
        "Clases de snorkel guiadas todos los martes y viernes a las 10:00 am. Incluye guía bilingüe y transporte al arrecife cercano. Costo: $45 USD.",
        "Zona de hamacas frente al mar con servicio de bar. Ideal para ver atardeceres. No requiere reservación.",
        "Seguridad acuática: 4 salvavidas certificados de 9:00 a 18:00. Banderas de seguridad: verde (seguro), amarilla (precaución), roja (prohibido nadar).",
    ],
    
    # ==========================================================================
    # 5. SPA Y GIMNASIO
    # ==========================================================================
    "spa_gym": [
        "Spa 'Serenity': 1200m² de instalaciones, 12 cabinas de tratamiento, sauna, baño de vapor, jacuzzi termal. Horario: 9:00-21:00.",
        "Masajes disponibles: sueco ($95 USD/60min), piedras calientes ($120 USD/75min), deep tissue ($110 USD/60min), aromaterapia ($105 USD/60min).",
        "Tratamientos faciales: limpieza profunda ($85), anti-edad ($130), hidratación intensiva ($95). Todos incluyen masaje de cuello y hombros.",
        "Paquetes de spa: 'Día de Relajación' (3 hrs, masaje + facial + acceso a área húmeda: $220 USD), 'Romance para Dos' (cabina doble, 2hrs: $380 USD).",
        "Rituales mayas auténticos: temazcal ceremonial ($85 USD), masaje maya con hierbas ancestrales ($140 USD). Solo con reservación previa.",
        "Gimnasio Fitness Center: equipado con Technogym última generación, pesas libres, área de cardio con 20 máquinas, aire acondicionado. 24 horas.",
        "Clases grupales incluidas: yoga (7:00 am playa), pilates (8:30 am gym), zumba (17:00 gym), spinning (18:30 gym). Cupo limitado 15 personas.",
        "Entrenador personal disponible: sesión individual $60 USD/hora, paquete 5 sesiones $250 USD. Incluye plan nutricional personalizado.",
        "Vestuarios con lockers, duchas amplias, sauna seco y baño de vapor de acceso libre para huéspedes. Toallas y amenidades incluidas.",
        "Área de relajación post-tratamiento con té de hierbas, frutas frescas y agua vitaminizada. Revistas y música ambiental.",
    ],
    
    # ==========================================================================
    # 6. ACTIVIDADES Y ENTRETENIMIENTO
    # ==========================================================================
    "actividades": [
        "Programa diario de actividades: aerobics acuático (10:00 am), voleibol playa (11:00 am), yoga sunset (18:00), cine bajo estrellas (20:30).",
        "Club infantil 'Mini Paradise': 4-12 años, horario 9:00-13:00 y 15:00-20:00. Incluye manualidades, juegos, snacks. Supervisión certificada. Gratis.",
        "Teen Club: 13-17 años, Xbox, PlayStation 5, billar, ping pong, torneos. Horario: 14:00-22:00. Snacks y bebidas incluidas.",
        "Shows nocturnos: lunes (música en vivo jazz), miércoles (show mexicano folclórico), viernes (fiesta blanca DJ internacional), domingos (tributo a cantantes).",
        "Clases de cocina mexicana: todos los jueves 16:00-18:00. Aprende a hacer guacamole, tacos y margaritas. Costo: $55 USD, incluye degustación y recetario.",
        "Lecciones de español básico para turistas: martes y jueves 10:00-11:00 en biblioteca. Gratis, materiales incluidos.",
        "Biblioteca con +500 libros en varios idiomas, juegos de mesa, área de lectura climatizada. Horario: 8:00-22:00.",
        "Salón de juegos: billar profesional, ping pong, futbolito, ajedrez gigante. Abierto 24 horas. Sin cargo.",
        "Noches de karaoke: sábados 21:00 en bar Sunset Lounge. Más de 5000 canciones en español, inglés, francés. Lista de bebidas especial.",
    ],
    
    # ==========================================================================
    # 7. TOURS Y EXCURSIONES
    # ==========================================================================
    "tours": [
        "Tour Ruinas de Tulum: Salida 8:00 am, incluye transporte, guía arqueólogo, entrada, agua embotellada. Duración 4 horas. Precio: $75 USD.",
        "Excursión Chichén Itzá (Maravilla del Mundo): Día completo, salida 7:00 am. Incluye comida buffet, cenote, guía certificado. Precio: $140 USD.",
        "Nado con Tortugas Akumal: Salida 9:00 am, incluye equipo snorkel, guía marina, transporte. 3 horas. Precio: $65 USD. Eco-friendly.",
        "Cenote Dos Ojos (buceo/snorkel): Sistema de cuevas subterráneas, agua cristalina. Certificación no requerida. Incluye equipo y guía. Precio: $90 USD.",
        "Isla Mujeres en catamarán: Día completo, incluye snorkel, comida, barra libre, música. Salida 9:00 am, regreso 17:00. Precio: $120 USD.",
        "Tour gastronómico Playa del Carmen: Visita 5 restaurantes locales, prueba platillos auténticos, incluye bebidas. 4 horas. Precio: $95 USD.",
        "Trekking Reserva Sian Ka'an (Patrimonio UNESCO): 6 horas, incluye avistamiento de aves, paseo en lancha, guía naturalista. Precio: $130 USD.",
        "Zip-line y ATVs Selva Maya: Adrenalina pura, 7 tirolesas + recorrido ATVs + cenote. Incluye transporte y comida. 5 horas. Precio: $110 USD.",
        "Pesca deportiva medio día: Salida 6:00 am, barco privado, equipo profesional, capitán, bebidas. 4 horas. Precio: $450 USD (hasta 4 personas).",
        "Todas las excursiones requieren reservación 24 horas antes. Cancelación sin cargo hasta 12 horas antes. Recogida en lobby del hotel.",
    ],
    
    # ==========================================================================
    # 8. SERVICIOS ADICIONALES
    # ==========================================================================
    "servicios": [
        "WiFi de alta velocidad gratuito en todo el resort: 200 Mbps fibra óptica. No requiere contraseña, conexión automática.",
        "Estacionamiento: subterráneo techado, vigilancia 24/7, capacidad 150 vehículos. Costo: $15 USD/noche. Valet parking: $25 USD/noche.",
        "Servicio de lavandería: recolección diaria 8:00 am, entrega 24 horas. Precios: camisa $4, pantalón $5, vestido $7. Planchado express (+50%).",
        "Centro de negocios: 6 computadoras, impresora, escáner, fotocopiadora, sala de juntas (10 personas). Horario: 7:00-22:00. Servicio gratis.",
        "Servicio médico: doctor en sitio 24/7, enfermería equipada, medicamentos básicos. Consulta: $50 USD. Emergencias: sin cargo, transporte a hospital incluido.",
        "Transporte aeropuerto-hotel: servicio privado $85 USD (hasta 4 pax), compartido $45 USD/persona. Solicitar 48 hrs antes. Incluye agua y toalla refrescante.",
        "Renta de autos: desk de Hertz en lobby, autos desde $40 USD/día. Seguro total incluido. Entrega y recolección en hotel sin cargo.",
        "Concierge Premium: ayuda con reservaciones restaurantes externos, compra de boletos espectáculos, organización de eventos especiales. Servicio gratuito.",
        "Baby sitting profesional: $18 USD/hora, mínimo 3 horas. Personal certificado, verificación de antecedentes. Solicitar 24 hrs antes.",
        "Cambio de divisas: en recepción, tasas competitivas. Aceptamos USD, EUR, CAD. Cajero automático en lobby (retiro máx $5000 MXN).",
        "Servicio de maletas: almacenamiento gratuito día de checkout si vuelo es nocturno. Porteadores disponibles 24/7.",
    ],
    
    # ==========================================================================
    # 9. POLÍTICAS DEL HOTEL
    # ==========================================================================
    "politicas": [
        "Check-in regular: 15:00 hrs. Check-out: 12:00 hrs. Late check-out sujeto a disponibilidad con cargo adicional.",
        "Mascotas permitidas: perros y gatos hasta 10kg, máximo 2 por habitación. Cargo: $30 USD/noche. Áreas restringidas: restaurantes, albercas, spa.",
        "Política de cancelación: sin cargo hasta 7 días antes. 3-6 días antes: cargo 50%. Menos de 3 días: cargo 100%. No-show: cargo total.",
        "Depósito de garantía: $200 USD al check-in (tarjeta de crédito). Reembolso automático al checkout si no hay consumos adicionales.",
        "Edad mínima para check-in: 18 años. Menores deben estar acompañados de adulto responsable. ID oficial requerido.",
        "Política anti-tabaco: hotel 100% libre de humo en interiores. Áreas designadas para fumar en terrazas exteriores. Multa por fumar en habitación: $250 USD.",
        "Ruido: horario de silencio 23:00-7:00. Música en terrazas hasta 22:00. Respeto a otros huéspedes.",
        "Seguridad: acceso controlado con brazalete electrónico. Cámaras de vigilancia en áreas comunes. Cajas fuertes en habitaciones sin costo.",
        "Dress code restaurantes: casual elegante (no shorts, no chanclas) en Sakura y La Trattoria después de 18:00. Resto: casual relajado.",
        "Política de toallas y albornoz: uso exclusivo en instalaciones del hotel. Llevar a playa o tours tiene cargo de $50 USD por pieza.",
    ],
    
    # ==========================================================================
    # 10. INFORMACIÓN TURÍSTICA LOCAL
    # ==========================================================================
    "info_local": [
        "Centro de Tulum: 15 minutos en auto, zona bohemia con restaurantes, bares, tiendas artesanales. Taxi desde hotel: $10 USD.",
        "Ruinas de Tulum: 20 minutos, sitio arqueológico maya frente al mar. Entrada: $95 MXN. Mejor horario: 8:00 am (menos calor y turistas).",
        "Playa del Carmen: 45 minutos, Quinta Avenida con shopping, vida nocturna. Taxi: $35 USD. ADO bus desde terminal: $80 MXN.",
        "Cenotes cercanos: Gran Cenote (10 min), Dos Ojos (15 min), Car Wash (12 min). Entrada promedio: $200-350 MXN. Imperdibles para snorkel.",
        "Reserva Sian Ka'an: 30 minutos, biosfera UNESCO, tours de día completo. Llevar repelente biodegradable y bloqueador solar eco-friendly.",
        "Supermercado Chedraui: 10 minutos, abierto 7:00-23:00. Ideal para comprar snacks, bebidas, souvenirs a precio local.",
        "Farmacia Guadalajara 24hrs: 12 minutos del hotel. Medicamentos, productos de higiene. Acepta tarjetas.",
        "Hospitales: Hospital de Tulum (15 min), Hospital Riviera Maya (35 min en Playa). Emergencias: 911. Concierge asiste en coordinación.",
        "Transporte local: colectivos (combis) en carretera $30 MXN a Tulum centro. Taxis hotel-Tulum $150-200 MXN. Apps: Uber no disponible.",
        "Cajeros ATM: en Tulum centro y Playa del Carmen. Retiro máximo $8000 MXN. Comisión bancaria aprox $30-50 MXN.",
        "Clima: tropical, temperatura promedio 27°C. Época seca: nov-abr (mejor época). Lluvias: may-oct (más económico, menos turistas).",
        "Temporada alta: dic-abr, semana santa, verano. Reservar con anticipación. Temporada baja: may-nov (excepto jul-ago).",
    ],
    
    # ==========================================================================
    # 11. EVENTOS Y GRUPOS
    # ==========================================================================
    "eventos": [
        "Salones para eventos: 'Caribe' (200 pax teatro), 'Maya' (100 pax banquete), 'Terraza Sunset' (150 pax cocktail). Incluye equipo AV.",
        "Bodas en la playa: paquetes desde $3500 USD (ceremonia + cocktail 50 pax). Coordinador de bodas incluido. Decoración personalizable.",
        "Paquete 'Luna de Miel': upgrade habitación, champagne, desayuno en cama, cena romántica, masaje parejas. Precio: $450 USD.",
        "Grupos corporativos: descuento 15% para +20 habitaciones. Incluye sala de juntas, coffee breaks, equipo AV. Menús personalizados disponibles.",
        "Team building activities: rally playa, cocina mexicana en equipo, yoga grupal, olimpiadas acuáticas. Desde $45 USD/persona.",
        "Retiros de yoga/wellness: paquetes 3-7 días, incluye clases, alimentación saludable, spa, meditación. Instructores certificados. Desde $850 USD.",
        "Aniversarios y celebraciones: decoración de habitación ($75), pastel personalizado ($45), músico privado 1hr ($120). Reservar 48hrs antes.",
        "Salón de usos múltiples: capacidad 300 personas, pista de baile, DJ, iluminación profesional. Ideal para fiestas y recepciones.",
    ],
    
    # ==========================================================================
    # 12. SUSTENTABILIDAD Y RESPONSABILIDAD SOCIAL
    # ==========================================================================
    "sustentabilidad": [
        "Certificación LEED Gold: edificio sustentable, paneles solares generan 40% de energía consumida, sistema de captación de agua pluvial.",
        "Programa 'Cero Plásticos': no popotes, no botellas plásticas individuales, amenidades en dispensadores recargables, bolsas de tela en tienda.",
        "Alianza con Tortugas Tulum A.C.: protección de nidos, liberación de crías (may-oct), voluntariado huéspedes disponible sin costo.",
        "Huerto orgánico: cultivamos 30% de vegetales usados en restaurantes. Tours guiados gratuitos martes y jueves 9:00 am.",
        "Programa de reciclaje: contenedores diferenciados en habitaciones y áreas comunes. Compostaje de residuos orgánicos de cocina.",
        "Productos de limpieza biodegradables: 100% eco-friendly, no tóxicos. Amenidades de baño certificadas orgánicas y cruelty-free.",
        "Proyecto 'Arrecife Vivo': colaboración con biólogos marinos, reforestación de coral, snorkel consciente. Donación $5 USD por huésped voluntaria.",
        "Empleados locales: 95% del staff es de Quintana Roo. Capacitación continua, salarios justos, seguro médico completo.",
    ],
    
    # ==========================================================================
    # 13. PREGUNTAS FRECUENTES RESOLUCIÓN DE PROBLEMAS
    # ==========================================================================
    "troubleshooting": [
        "Problema: WiFi lento. Solución: Reconectar dispositivo, usar WiFi5G (Paradise-5G). Si persiste, reportar a recepción ext. 0 para reset.",
        "Problema: Aire acondicionado no enfría. Solución: Verificar que puertas/ventanas estén cerradas, temp mínima 18°C. Reportar a mantenimiento ext. 300.",
        "Problema: No hay agua caliente. Solución: Esperar 3 minutos (calentador solar), dejar correr. Si persiste, llamar ext. 300 (mantenimiento 24hrs).",
        "Problema: Caja fuerte no abre. Solución: Verificar código (4 dígitos), batería baja (luz roja). Recepción abre con llave maestra sin cargo.",
        "Problema: Ruido de habitación contigua. Solución: Llamar a recepción ext. 0, hablarán con huésped o cambiarán su habitación si disponible.",
        "Problema: Reservación de restaurante no aparece. Solución: Verificar confirmación por WhatsApp/email. Concierge resolverá o buscará alternativa.",
        "Problema: Olvidé algo en la habitación (checkout). Solución: Llamar 24hrs, guardan objetos 30 días. Envío internacional con costo del huésped.",
        "Problema: Cargo incorrecto en cuenta. Solución: Solicitar desglose detallado en recepción, corrección inmediata si hay error comprobado.",
        "Problema: Alergia alimentaria no respetada. Solución: Informar inmediatamente a manager de restaurante, preparación especial sin cargo, disculpa formal.",
        "Problema: Transporte aeropuerto no llegó. Solución: Llamar concierge, enviarán taxi inmediato sin cargo adicional más compensación.",
    ],
    
    # ==========================================================================
    # 14. NÚMEROS Y EXTENSIONES IMPORTANTES
    # ==========================================================================
    "contactos": [
        "Recepción (24hrs): Extensión 0 desde habitación, +52 (984) 871-2500 desde celular.",
        "Room Service (24hrs): Extensión 100, WhatsApp +52 (984) 871-2510.",
        "Concierge: Extensión 200, horario 7:00-23:00.",
        "Mantenimiento: Extensión 300 (24hrs), problemas técnicos urgentes.",
        "Spa: Extensión 400, reservaciones 9:00-20:00.",
        "Restaurante Sakura: Extensión 501, La Trattoria: Extensión 502.",
        "Emergencias médicas: Extensión 911 o botón rojo junto a teléfono.",
        "Seguridad: Extensión 700 (24hrs), cualquier situación irregular.",
        "Botones/Valet: Extensión 800, apoyo con maletas o estacionamiento.",
        "Operadora: Extensión 9, asistencia para llamadas externas o dudas.",
    ],
}


def generate_master_document():
    """
    Genera el archivo maestro de texto que será leído por ingest.py
    """
    # Definir rutas (relativo al script)
    script_dir = Path(__file__).parent
    output_file = script_dir / "hotel_paradise_resort_manual.txt"
    
    print("\n" + "="*60)
    print("📝 GENERANDO DOCUMENTO MAESTRO DEL HOTEL")
    print("="*60 + "\n")
    
    print(f"📂 Carpeta de destino: {script_dir}")
    print(f"📄 Archivo: {output_file.name}")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            # Encabezado del documento
            f.write("="*70 + "\n")
            f.write("MANUAL OPERATIVO Y DE INFORMACIÓN\n")
            f.write("HOTEL PARADISE RESORT - RIVIERA MAYA, MÉXICO\n")
            f.write("="*70 + "\n\n")
            
            f.write(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Versión: 1.0\n")
            f.write(f"Categorías: {len(HOTEL_INFO)}\n")
            
            total_items = sum(len(items) for items in HOTEL_INFO.values())
            f.write(f"Documentos: {total_items}\n\n")
            
            f.write("Este documento contiene toda la información del hotel que será\n")
            f.write("utilizada por el asistente virtual para responder consultas de huéspedes.\n\n")
            
            f.write("="*70 + "\n\n")
            
            # Escribir cada categoría
            for i, (category, items) in enumerate(HOTEL_INFO.items(), 1):
                # Título de sección legible
                title = category.replace("_", " ").upper()
                
                f.write("\n" + "-"*70 + "\n")
                f.write(f"SECCIÓN {i}: {title}\n")
                f.write("-"*70 + "\n\n")
                
                # Escribir cada item de la categoría
                for j, item in enumerate(items, 1):
                    f.write(f"{j}. {item}\n\n")
                
                print(f"✅ Sección '{title}': {len(items)} items escritos")
            
            # Pie de página
            f.write("\n" + "="*70 + "\n")
            f.write("FIN DEL DOCUMENTO\n")
            f.write("="*70 + "\n")
        
        # Estadísticas finales
        file_size = output_file.stat().st_size
        print(f"\n{'='*60}")
        print(f"✅ DOCUMENTO GENERADO EXITOSAMENTE")
        print(f"{'='*60}")
        print(f"📊 Estadísticas:")
        print(f"   - Archivo: {output_file.name}")
        print(f"   - Tamaño: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        print(f"   - Categorías: {len(HOTEL_INFO)}")
        print(f"   - Items totales: {total_items}")
        print(f"\n🎯 Siguiente paso:")
        print(f"   Ejecuta: python ingest.py")
        print(f"   (desde la raíz del proyecto)\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    success = generate_master_document()
    exit(0 if success else 1)
