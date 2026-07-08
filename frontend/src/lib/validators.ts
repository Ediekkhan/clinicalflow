'use client';

import { useState } from 'react';

export const validators = {
  phone: (value: string): string | null => {
    const cleaned = value.replace(/\D/g, '');
    const local = cleaned.startsWith('234') ? cleaned.slice(3) : cleaned.startsWith('0') ? cleaned.slice(1) : cleaned;
    if (local.length !== 10) return 'Enter a valid 10-digit Nigerian phone number';
    return null;
  },
  password: (value: string): string | null => {
    if (value.length < 8) return 'At least 8 characters required';
    if (!/[A-Z]/.test(value)) return 'Include at least one uppercase letter';
    if (!/[0-9]/.test(value)) return 'Include at least one number';
    return null;
  },
  pin: (value: string): string | null => {
    if (!/^\d{4}$/.test(value)) return 'PIN must be exactly 4 digits';
    if (['0000', '1111', '1234', '4321', '2222', '3333'].includes(value)) return 'Choose a less predictable PIN';
    return null;
  },
  symptomText: (value: string): string | null => {
    if (value.trim().length < 10) return 'Please describe your symptoms in more detail';
    if (value.length > 2000) return 'Too long - maximum 2000 characters';
    return null;
  },
};

export function useFormValidation<T extends Record<string, string>>(
  initialValues: T,
  validationRules: Partial<Record<keyof T, (value: string) => string | null>>,
) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({});
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({});

  const validate = (field: keyof T, value: string) => {
    const rule = validationRules[field];
    if (!rule) return true;
    const error = rule(value);
    setErrors((previous) => ({ ...previous, [field]: error || undefined }));
    return !error;
  };

  const handleChange = (field: keyof T, value: string) => {
    setValues((previous) => ({ ...previous, [field]: value }));
    if (touched[field]) validate(field, value);
  };

  const handleBlur = (field: keyof T) => {
    setTouched((previous) => ({ ...previous, [field]: true }));
    validate(field, values[field]);
  };

  const validateAll = () => {
    let valid = true;
    Object.keys(validationRules).forEach((field) => {
      if (!validate(field as keyof T, values[field as keyof T])) valid = false;
    });
    return valid;
  };

  return { values, errors, touched, handleChange, handleBlur, validateAll };
}

