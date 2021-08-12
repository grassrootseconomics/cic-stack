// Third party imports
import { validatePerson, validateVcard } from '@cicnet/schemas-data-validator';

/**
 * Validates a person object against the defined Person schema.
 *
 * @param person - A person object to be validated.
 */
async function personValidation(person: any): Promise<void> {
  const personValidationErrors: any = await validatePerson(person);

  if (personValidationErrors) {
    personValidationErrors.map((error) => console.error(`${error.message}`, person, error));
  }
}

/**
 * Validates a vcard object against the defined Vcard schema.
 *
 * @param vcard - A vcard object to be validated.
 */
async function vcardValidation(vcard: any): Promise<void> {
  const vcardValidationErrors: any = await validateVcard(vcard);

  if (vcardValidationErrors) {
    vcardValidationErrors.map((error) => console.error(`${error.message}`, vcard, error));
  }
}

/** @exports */
export { personValidation, vcardValidation };
