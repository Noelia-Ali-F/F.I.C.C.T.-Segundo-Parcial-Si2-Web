export type TechnicianStatus = 'disponible' | 'ocupado' | 'fuera_de_servicio';
export type TechnicianFilter = 'activos' | 'todos' | 'historial';

export type Technician = {
  id: number;
  workshop_id: number | null;
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
  created_at: string;
  updated_at: string;
};

export type TechnicianFormModel = {
  full_name: string;
  phone: string;
  email: string;
  specialty: string;
  status: TechnicianStatus;
};

export const TECHNICIAN_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];
