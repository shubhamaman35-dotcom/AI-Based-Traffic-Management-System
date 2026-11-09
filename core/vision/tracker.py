"""
Multi-Object Centroid Tracker
Associates bounding boxes across frames to maintain unique vehicle IDs,
calculate vehicle velocity vectors, and trigger line-crossing events.
"""

from collections import OrderedDict
import numpy as np
import math


class TrackedVehicle:
    def __init__(self, object_id: int, centroid: tuple, bbox: tuple, label: str):
        self.object_id = object_id
        self.centroid = centroid
        self.bbox = bbox # (x, y, w, h)
        self.label = label
        self.disappeared = 0
        self.trajectory = [centroid]
        self.speed_px_per_sec = 0.0
        self.has_counted = False


class CentroidTracker:
    def __init__(self, max_disappeared: int = 25, max_distance: float = 60.0):
        self.next_object_id = 1
        self.objects = OrderedDict()
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, centroid: tuple, bbox: tuple, label: str):
        self.objects[self.next_object_id] = TrackedVehicle(
            self.next_object_id, centroid, bbox, label
        )
        self.next_object_id += 1

    def deregister(self, object_id: int):
        if object_id in self.objects:
            del self.objects[object_id]

    def update(self, detections: list, dt: float = 0.033) -> list:
        """
        Takes list of detections [(x, y, w, h, label, score), ...]
        Returns list of active TrackedVehicle instances.
        """
        if len(detections) == 0:
            for object_id in list(self.objects.keys()):
                self.objects[object_id].disappeared += 1
                if self.objects[object_id].disappeared > self.max_disappeared:
                    self.deregister(object_id)
            return list(self.objects.values())

        # Calculate centroids of input detections
        input_centroids = np.zeros((len(detections), 2), dtype="int")
        for i, (x, y, w, h, _, _) in enumerate(detections):
            input_centroids[i] = (int(x + w / 2.0), int(y + h / 2.0))

        if len(self.objects) == 0:
            for i in range(len(detections)):
                x, y, w, h, label, _ = detections[i]
                self.register(tuple(input_centroids[i]), (x, y, w, h), label)
        else:
            object_ids = list(self.objects.keys())
            object_centroids = [obj.centroid for obj in self.objects.values()]

            # Compute Euclidean distances between existing and incoming centroids
            D = np.zeros((len(object_centroids), len(input_centroids)), dtype="float")
            for i, o_c in enumerate(object_centroids):
                for j, i_c in enumerate(input_centroids):
                    D[i, j] = math.hypot(o_c[0] - i_c[0], o_c[1] - i_c[1])

            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            used_rows = set()
            used_cols = set()

            for row, col in zip(rows, cols):
                if row in used_rows or col in used_cols:
                    continue

                if D[row, col] > self.max_distance:
                    continue

                object_id = object_ids[row]
                new_c = tuple(input_centroids[col])
                x, y, w, h, label, _ = detections[col]

                # Update speed
                old_c = self.objects[object_id].centroid
                dist_traveled = math.hypot(new_c[0] - old_c[0], new_c[1] - old_c[1])
                self.objects[object_id].speed_px_per_sec = dist_traveled / max(0.001, dt)

                self.objects[object_id].centroid = new_c
                self.objects[object_id].bbox = (x, y, w, h)
                self.objects[object_id].label = label
                self.objects[object_id].disappeared = 0
                self.objects[object_id].trajectory.append(new_c)
                if len(self.objects[object_id].trajectory) > 30:
                    self.objects[object_id].trajectory.pop(0)

                used_rows.add(row)
                used_cols.add(col)

            unused_rows = set(range(0, D.shape[0])).difference(used_rows)
            unused_cols = set(range(0, D.shape[1])).difference(used_cols)

            for row in unused_rows:
                object_id = object_ids[row]
                self.objects[object_id].disappeared += 1
                if self.objects[object_id].disappeared > self.max_disappeared:
                    self.deregister(object_id)

            for col in unused_cols:
                x, y, w, h, label, _ = detections[col]
                self.register(tuple(input_centroids[col]), (x, y, w, h), label)

        return list(self.objects.values())
