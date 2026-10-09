import { describe, expect, it } from 'vitest'
import { dateTime, localToUtc, priceLabel, propertyLabel, telHref } from '../format.js'

describe('format', () => {
  it('formate les prix sans inventer de valeur', () => {
    expect(priceLabel({})).toBe('Prix non renseigné')
    expect(priceLabel({ annual_rent: 360000 })).toMatch(/360.000 € \/an/)
  })
  it('construit un libellé de bien', () => {
    expect(propertyLabel({ property_type: 'entrepot', city: 'Lyon' })).toBe('Entrepôt – Lyon')
  })
  it('nettoie les numéros pour le composeur', () => {
    expect(telHref('06 00 00 00 03')).toBe('tel:0600000003')
    expect(telHref('+33 (0)1 23')).toBe('tel:+33(0)123'.replace(/[()]/g, ''))
  })
  it('interprète les horodatages API comme UTC', () => {
    const iso = localToUtc('2030-01-15T10:00')
    expect(iso).toMatch(/^2030-01-15T\d\d:00:00$/)
    expect(dateTime(iso)).toContain('15/01/2030')
  })
})
