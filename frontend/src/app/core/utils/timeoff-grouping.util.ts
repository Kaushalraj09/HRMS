import { TimeOffRequest, GroupedTimeOffRequest } from '../models/timeoff.model';

export function groupTimeOffRequests(requests: TimeOffRequest[]): GroupedTimeOffRequest[] {
  const groupedList: GroupedTimeOffRequest[] = [];
  const processedIds = new Set<number>();

  for (const req of requests) {
    if (processedIds.has(req.id)) {
      continue;
    }

    if (req.batch_id) {
      // Find all requests in this batch
      const batchRequests = requests.filter(r => r.batch_id === req.batch_id);
      
      // Sort by date ascending
      batchRequests.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      
      batchRequests.forEach(r => processedIds.add(r.id));
      
      const totalDuration = batchRequests.reduce((sum, r) => sum + r.duration_hours, 0);

      groupedList.push({
        id: req.batch_id,
        isGrouped: batchRequests.length > 1,
        requests: batchRequests,
        employee_id: req.employee_id,
        employee_name: req.employee_name,
        leave_type: req.leave_type,
        startDate: batchRequests[0].date,
        endDate: batchRequests[batchRequests.length - 1].date,
        totalDurationHours: totalDuration,
        status: req.status, // assume all requests in a batch have the same status
        reason: req.reason,
        attachment_name: req.attachment_name,
        start_time: req.start_time,
        end_time: req.end_time
      });
    } else {
      // Legacy request without batch_id, just wrap it
      processedIds.add(req.id);
      groupedList.push({
        id: req.id.toString(),
        isGrouped: false,
        requests: [req],
        employee_id: req.employee_id,
        employee_name: req.employee_name,
        leave_type: req.leave_type,
        startDate: req.date,
        endDate: req.date,
        totalDurationHours: req.duration_hours,
        status: req.status,
        reason: req.reason,
        attachment_name: req.attachment_name,
        start_time: req.start_time,
        end_time: req.end_time
      });
    }
  }

  // Final sort by startDate descending
  groupedList.sort((a, b) => new Date(b.startDate).getTime() - new Date(a.startDate).getTime());
  
  return groupedList;
}
