"""
The objopenmc - An object-oriented paradigm wrapper for OpenMC Python API

Copyright (C) 2026 S. V. Litash

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program (see LICENSE file). If not, see <https://www.gnu.org/licenses/>.

"""

from abc import ABC, abstractmethod
#from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import openmc
import CAD_to_OpenMC

@dataclass
class BaseMaterial:
    name: str
    density: float
    density_units: str
    percent_type: str
    nuclides: Dict[str, float] = field(default_factory=dict)
    elements: Dict[str, float] = field(default_factory=dict)
    sab_tables: List[str] = field(default_factory=list)

    def make_openmc_material(self, temperature: Optional[float] = None, instance_id: Optional[str] = None) -> openmc.Material:
        mat_name = f"{self.name}_{instance_id}" if instance_id else self.name
        mat = openmc.Material(name=mat_name)
        mat.set_density(self.density_units, self.density)

        for nucleides_count, fraction in self.nuclides.items():
            mat.add_nuclide(nucleides_count, fraction, percent_type=self.percent_type)

        for elements_count, fraction in self.elements.items():
            mat.add_element(elements_count, fraction, percent_type=self.percent_type)

        for sab in self.sab_tables:
            mat.add_s_alpha_beta(sab)

        if temperature is not None:
            mat.temperature = temperature

        return mat

class BaseBody(ABC):
    def __init__(self, name: str, material: Optional[BaseMaterial] = None, temperature: Optional[float] = None, volume: Optional[float] = None):
        self.name = name
        self.material = material
        self.temperature = temperature

    @abstractmethod
    def get_openmc_material(self) -> Optional[openmc.Material]:
        if self.material is None:
            return None

        return self.material.make_openmc_material(temperature = self.temperature, instance_id = self.name)

class BoundaryBody(BaseBody):
    def __init__(self, name: str, region: openmc.Region, boundary_type: str = "vacuum"):
        super().__init__(name=name, material=None, temperature=None)
        self.region = region
        self.boundary_type = boundary_type

    def build_cell() -> openmc.Cell:
        cell = openmc.Cell(name=self.name, region=self.region, fill=None)
        return cell

class CADUnitBody(BaseBody):
    def __init__(self, name: str, cad_filename: str, material: BaseMaterial, temperature: Optional[float], meshing_parameters: Optional[Dict[str, Any]] = None):
        super().__init__(name = name, material = material, temperature = temperature)
        self.cad_filename = cad_filename
        self.meshing_parameters = meshing_parameters or {}

class CSGBodyUnit(BaseBody):
    def __init__(self, name: str, region: openmc.Region, material: Optional[BaseMaterial] = None, temperature: Optional[float] = None):
        super().__init__(name=name, material=material, temperature=temperature)
        self.region = region

    def build_cell() -> openmc.Cell:
        cell = openmc.Cell(name=self.name, region=self.region)
        cell.fill = self.get_openmc_material()

        if self.temperature is not None:
            cell.temperature = self.temperature

        return cell
