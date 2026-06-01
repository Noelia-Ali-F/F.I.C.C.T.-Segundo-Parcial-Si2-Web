export type WorkshopApprovalStatus = 'pendiente' | 'activo' | 'rechazado';

export type WorkshopRegistration = {
  id: number;
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  approval_status: WorkshopApprovalStatus;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
  utc_offset_minutes: number | null;
  created_at: string;
};

export type WorkshopFormModel = {
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  latitude: number | null;
  longitude: number | null;
  password: string;
};

export type WorkshopUpdatePayload = {
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
  utc_offset_minutes: number | null;
  password: string;
};

export const WORKSHOP_ZONE_OPTIONS = [
  'zona norte',
  'zona sur',
  'zona este',
  'zona oeste',
  'zona centro',
];

export const WORKSHOP_SPECIALTY_OPTIONS = [
  'Batería',
  'Neumático',
  'Combustible',
  'Motor',
  'Sistema eléctrico',
  'Accidente',
  'Cerrajería / llaves',
];
