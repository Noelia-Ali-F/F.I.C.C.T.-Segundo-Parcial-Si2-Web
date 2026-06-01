export type ClientStatus = 'active' | 'suspended';

export type Client = {
  id: number;
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
  created_at: string;
  updated_at: string;
};

export type ClientFormModel = {
  identity_card: string;
  full_name: string;
  email: string;
  phone: string;
  password: string;
  role: string;
  status: ClientStatus;
  accepted_terms: boolean;
};
