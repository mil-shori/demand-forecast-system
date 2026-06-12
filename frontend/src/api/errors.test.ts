import { AxiosError, AxiosResponse } from 'axios'

import { getApiErrorMessage } from './errors'

const FALLBACK = 'デフォルトのエラーメッセージ'

function makeAxiosError(data: unknown): AxiosError {
  const response = {
    data,
    status: 400,
    statusText: 'Bad Request',
    headers: {},
    config: {},
  } as AxiosResponse
  return new AxiosError('Request failed', 'ERR_BAD_REQUEST', undefined, undefined, response)
}

describe('getApiErrorMessage', () => {
  it('FastAPIのdetail文字列をそのまま返す', () => {
    const error = makeAxiosError({ detail: 'freee連携が未設定です' })
    expect(getApiErrorMessage(error, FALLBACK)).toBe('freee連携が未設定です')
  })

  it('detailが無いレスポンスはフォールバックを返す', () => {
    const error = makeAxiosError({ message: 'other shape' })
    expect(getApiErrorMessage(error, FALLBACK)).toBe(FALLBACK)
  })

  it('detailが文字列以外（バリデーションエラー配列など）はフォールバックを返す', () => {
    const error = makeAxiosError({
      detail: [{ loc: ['body', 'amount'], msg: 'value error' }],
    })
    expect(getApiErrorMessage(error, FALLBACK)).toBe(FALLBACK)
  })

  it('レスポンスの無いaxiosエラー（ネットワークエラー）はフォールバックを返す', () => {
    const error = new AxiosError('Network Error', 'ERR_NETWORK')
    expect(getApiErrorMessage(error, FALLBACK)).toBe(FALLBACK)
  })

  it('axios以外のエラーはフォールバックを返す', () => {
    expect(getApiErrorMessage(new Error('boom'), FALLBACK)).toBe(FALLBACK)
    expect(getApiErrorMessage('string error', FALLBACK)).toBe(FALLBACK)
    expect(getApiErrorMessage(undefined, FALLBACK)).toBe(FALLBACK)
  })
})
