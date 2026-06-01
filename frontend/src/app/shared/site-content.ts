export type FeatureCard = {
  title: string;
  description: string;
  detail?: string;
};

export type SectionContent = {
  eyebrow: string;
  title: string;
  intro: string;
  lead: string;
  highlight: string;
  cards: FeatureCard[];
  cta: string;
};

export const heroHighlights = [
  'Eventos exclusivos y activaciones deportivas',
  'Auxilio mecánico y asistencia vehicular',
  'Licencias internacionales y escuela de conducción',
];

export const serviceCards: FeatureCard[] = [
  {
    title: 'Auxilio Mecánico',
    description: 'Cobertura pensada para acompañarte en ruta con rapidez, confianza y atención humana.',
  },
  {
    title: 'Escuela de Conducción',
    description: 'Formación teórica y práctica con una comunicación clara, cercana y orientada a seguridad vial.',
  },
  {
    title: 'Licencia Internacional',
    description: 'Un proceso simple y bien explicado para conductores que necesitan movilidad fuera del país.',
  },
  {
    title: 'Asistencia Vehicular',
    description: 'Respuesta operativa para imprevistos, remolque y acompañamiento cuando más lo necesitas.',
  },
  {
    title: 'Salones y Eventos',
    description: 'Espacios versátiles para reuniones, celebraciones, networking y actividades institucionales.',
  },
  {
    title: 'Seguro Automotor',
    description: 'Coberturas adaptadas a necesidades reales, explicadas sin fricción ni lenguaje innecesario.',
  },
];

export const newsCards: FeatureCard[] = [
  {
    title: 'Reconocimiento institucional',
    description: 'Celebración del aniversario del club con presencia de filiales y aliados estratégicos.',
  },
  {
    title: 'Campaña de seguridad vial',
    description: 'Entrega de cascos homologados y activaciones con policías, militares y repartidores.',
  },
  {
    title: 'Seguro automotor',
    description: 'Acciones comerciales enfocadas en comodidad, bienestar y soluciones para la familia.',
  },
];

export const faqItems: FeatureCard[] = [
  {
    title: '¿Cómo obtengo la licencia internacional?',
    description: 'Se centraliza la información en una sola vista para reducir dudas y facilitar la conversión.',
  },
  {
    title: '¿Qué incluyen las clases de conducción?',
    description: 'Gabinete, práctica, educación vial y una sesión de mecánica básica con horarios visibles.',
  },
  {
    title: '¿Hay cursos ejecutivos de fin de semana?',
    description: 'Sí, con estructura pensada para personas con menos disponibilidad en la semana.',
  },
];

export const sectionContent: Record<string, SectionContent> = {
  servicios: {
    eyebrow: 'Servicios',
    title: 'Soluciones para el socio y su familia',
    intro:
      'Este bloque reúne los servicios de mayor valor práctico, manteniendo la lógica del sitio de referencia pero con una presentación más ordenada y moderna.',
    lead:
      'La idea es que cada servicio tenga un mensaje corto, comprensible y orientado a la acción.',
    highlight: 'El usuario debería entender en segundos qué ofrece el club y por qué le sirve.',
    cards: serviceCards,
    cta: 'Solicitar información',
  },
  escuela: {
    eyebrow: 'Formación',
    title: 'Escuela de conducción',
    intro:
      'Una de las secciones más importantes por intención comercial. Aquí conviene mostrar modalidades, tiempos, requisitos y beneficios con mucha claridad.',
    lead:
      'La estructura está pensada para ayudar a convertir visitantes en consultas reales sin perder el tono institucional.',
    highlight: 'Más claridad en horarios y requisitos reduce fricción y aumenta confianza.',
    cards: [
      {
        title: 'Curso regular',
        description: 'Programa progresivo con teoría, simulador, práctica y base de mecánica.',
      },
      {
        title: 'Clases de moto',
        description: 'Entrenamiento enfocado en control, seguridad y técnica para motociclistas.',
      },
      {
        title: 'Manejo defensivo',
        description: 'Capacitación para empresas, instituciones y conductores que priorizan prevención.',
      },
      {
        title: 'Educación vial',
        description: 'Contenido que refuerza buenas prácticas y conducción responsable.',
      },
    ],
    cta: 'Reservar un cupo',
  },
  contacto: {
    eyebrow: 'Contacto',
    title: 'Atención clara y accesible',
    intro: 'Estamos aqui para ayudarte. Contactanos de forma rapida y sencilla.',
    lead: 'Informacion de contacto disponible 24/7.',
    highlight: 'Respuesta clara, directa y confiable.',
    cards: [],
    cta: 'Contactanos ahora',
  },
};
