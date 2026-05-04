from typing import List

from src.files.file_bucket import FileBucket
from src.files.file_record import FileRecord

class SizeFileStrategy:
  def __init__(self, bucket_size_mb: float) -> None:
    self._bucket_size_bytes = bucket_size_mb * 1024 * 1024
    
  def bucket(self, files: List[FileRecord]) -> List[FileBucket]:
    if not files:
      return []
    
    buckets: List[FileBucket] = []
    current_bucket = FileBucket(max_size_bytes=self._bucket_size_bytes)
    
    for file in files:
      if file.size_bytes > self._bucket_size_bytes:
        if current_bucket.files:
          buckets.append(current_bucket)
          current_bucket = FileBucket(max_size_bytes=self._bucket_size_bytes)
        oversized = FileBucket(max_size_bytes=file.size_bytes)
        oversized.add(file)
        buckets.append(oversized)
      elif current_bucket.can_fit(file):
        current_bucket.add(file)
      else:
        buckets.append(current_bucket)
        current_bucket = FileBucket(max_size_bytes=self._bucket_size_bytes)
        current_bucket.add(file)

    if current_bucket.files:
      buckets.append(current_bucket)

    return buckets