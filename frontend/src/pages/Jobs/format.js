export const payLabel = (job) =>
  `${job.pay_type === 'daily' ? '일급' : '시급'} ${job.pay_amount.toLocaleString()}원`

export const timeLabel = (job) =>
  `${job.start_time.slice(0, 5)}~${job.end_time.slice(0, 5)}`