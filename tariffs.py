import math
from dataclasses import dataclass, field

import pandas as pd
import matplotlib.pyplot as plt

@dataclass
class Rate:
  name: str
  unit_rate: float
  start_time: str  # HH:MM
  end_time: str  # HH:MM

@dataclass
class Tariff:
  name: str
  day_unit_rate: float
  standing_charge: float = field(default=0)
  additional_rates: list[Rate] = field(default_factory=list)

  _unit_rate_lookup: pd.Series = field(init=False)

  def __post_init__(self):
    self._unit_rate_lookup = Tariff.compile_unit_rate_lookup(self.day_unit_rate, self.additional_rates)

  def lookup(self, time: str) -> float:
    return self._unit_rate_lookup[pd.Timedelta(time + ":00")]

  def plot(self, ax=None):
    show = ax is None
    data = self._unit_rate_lookup

    if ax is None:
      _, ax = plt.subplots(figsize=(10, 5))

    # Plot the data on the provided ax
    ax.plot(data.index.total_seconds() / 60, data.values, label=self.name)  # Convert Timedelta to minutes for plotting
    if show:
      ax.set_title(f"{self.name} Tarrif")
    ax.set_xlabel("Time of Day")
    ax.set_ylabel("Unit Rate (p/kWh)")
    ax.grid(True)

    # Set the x-axis ticks manually at each hour (in minutes)
    hour_ticks = range(0, 24 * 60 + 1, 60)
    ax.set_xticks(hour_ticks)

    # Format the x-axis labels to show "HH:MM"
    hour_labels = [f"{h:02d}:00" for h in range(25)]
    ax.set_xticklabels(hour_labels)

    # Rotate the x-axis labels for better readability
    ax.tick_params(axis="x", rotation=45)

    if show:
      # Set the y-axis ticks manually to each pence
      max_pence = math.ceil(max(data) / 10) * 10
      pence_ticks = [*range(0, max_pence, 10), max_pence]
      ax.set_yticks(pence_ticks)

      # Format the y-axis labels to show 2dp
      pence_labels = [str(p) for p in pence_ticks]
      ax.set_yticklabels(pence_labels)

    if show:
      plt.show()

  def __str__(self):
    builder = f"Tariff: {self.name}\n"
    builder += f"Day unit rate: {self.day_unit_rate} p/kWh\n"
    for rate in self.additional_rates:
      builder += f"{rate.name} ({rate.start_time} - {rate.end_time}): {rate.unit_rate} p/kWh\n"
    builder += f"Standing charge: {self.standing_charge} p\n"
    return builder

  @staticmethod
  def compile_unit_rate_lookup(day_unit_rate: float, additional_rates: list[Rate]) -> pd.Series:
    # Create a full day's worth of minutes
    minutes = pd.timedelta_range(start="00:00:00", periods=24 * 60, freq="min")

    # Initialize the pandas Series with the default (day) rate
    lookup = pd.Series(day_unit_rate, index=minutes)

    # Update the Series with additional rates
    for rate in additional_rates:
      start_time = pd.to_timedelta(rate.start_time + ":00")
      end_time = pd.to_timedelta(rate.end_time + ":00")
      
      if start_time == end_time:
        lookup[start_time] = rate.unit_rate
      elif start_time < end_time:
        mask = (lookup.index >= start_time) & (lookup.index < end_time)
        lookup[mask] = rate.unit_rate
      else:
        # Overnight rate, split into two parts
        mask1 = (lookup.index >= start_time)
        mask2 = (lookup.index < end_time)
        lookup[mask1] = rate.unit_rate
        lookup[mask2] = rate.unit_rate

    return lookup
