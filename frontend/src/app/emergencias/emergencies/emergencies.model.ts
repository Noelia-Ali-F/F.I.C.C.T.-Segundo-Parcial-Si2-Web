export type EmergencyStatus = 'pendiente' | 'activo' | 'rechazado';

export type EmergencyReport = {
  id: number;
  client_id: number | null;
  client_name: string | null;
  vehicle_name: string;
  vehicle_plate: string;
  problem_type: string;
  price: number | null;
  emergency_status: EmergencyStatus | null;
  problem_type_standardized: string | null;
  description: string | null;
  audio_transcript: string | null;
  photo_paths?: string[] | string | null;
  photo_urls: string[] | string | null;
  audio_url: string | null;
  latitude: number | null;
  longitude: number | null;
  address: string | null;
  zone: string | null;
  nearest_workshop_id: number | null;
  nearest_workshop_name: string | null;
  nearest_workshop_specialty: string | null;
  nearest_workshop_zone: string | null;
  nearest_workshop_distance_meters: number | null;
  assignment_id: number | null;
  assignment_status: string | null;
  assigned_technician_id: number | null;
  assigned_technician_name: string | null;
  assigned_technician_phone: string | null;
  assigned_technician_email: string | null;
  assigned_technician_specialty: string | null;
  created_at: string;
};

export type MaintenanceRequest = {
  id: number;
  code: string;
  client: string;
  vehicle: string;
  location: string;
  priority: 'Alta' | 'Media' | 'Baja';
  status: EmergencyStatus;
  price: number | null;
  distance: string;
  detail: string;
  reportedAt: string;
  createdAt: string;
  latitude: number | null;
  longitude: number | null;
  nearestWorkshopId: number | null;
  nearestWorkshopName: string | null;
  problemType: string;
  standardizedProblemType: string | null;
  clientDescription: string | null;
  audioTranscript: string | null;
  photoUrls: string[];
  audioUrl: string | null;
  assignmentId: number | null;
  assignmentStatus: string | null;
  assignedTechnicianId: number | null;
  assignedTechnicianName: string | null;
  assignedTechnicianPhone: string | null;
  assignedTechnicianSpecialty: string | null;
};

export type AuditTone = 'info' | 'success' | 'warning' | 'danger';

export type AuditItem = {
  title: string;
  detail: string;
  meta: string;
  createdAt: string;
  tone: AuditTone;
};
