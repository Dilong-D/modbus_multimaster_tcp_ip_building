import datetime


# First Order ODE (y' = ub(x, y)) Solver using Euler method
# xa: initial value of independent variable
# xb: final value of independent variable
# ya: initial value of dependent variable
# n : number of steps (higher the better)
# Returns value of y at xb.
def Euler(f, xa, xb, ya, n):
	h = (xb - xa) / float(n)
	x = xa
	y = ya
	for i in range(n):
		y += h * f(x, y)
		x += h
	return y


def get_h(timestamp):
	return datetime.datetime.fromtimestamp(timestamp).hour


class Building:
	def __init__(self):
		# constants variable for simulation
		self.M_H = 3000
		self.C_H = 2700.0
		self.K_H = 12000
		self.F_MAX = 40 / 3600
		self.M_B = 20000.0
		self.C_B = 1000.0
		self.K_E = 15000.0
		self.C_W = 4200.0
		self.RO = 1000.0
		self.K_P = 0.0016  # wzmocnienie z simulinka
		self.K_I = 6.8  # stala calkowania z simulinka

		self.t_cob = 290.0
		self.t_ro = 280.0
		self.ub = 0.5
		self.t_ref = 293  # temperatura referencyjan pomieszczenia (taka chcemy w budynku)
		self.integral = 0  # calka do czlonu calkujacego regulatora
		self.f_cob = self.ub * self.F_MAX
		self.t_zco = 350
		self.t_o = 277
		self.t0 = 0
		self.time = (datetime.datetime.fromtimestamp(0).strftime('%Y-%m-%d %H:%M:%S'))

	def building_simulation_step(self, t0_arg, dt, t_zco_arg, t_o_arg):
		self.time = (datetime.datetime.fromtimestamp(int(t0_arg)).strftime('%Y-%m-%d %H:%M:%S'))

		hour = get_h(t0_arg)
		if hour > 6 & hour < 21:
			self.t_ref = 293.15
		else:
			self.t_ref = 288.15

		self.t0 = t0_arg
		t1 = self.t0 + dt

		self.t_zco = t_zco_arg
		self.t_o = t_o_arg
		error = self.t_ref - self.t_ro  # obliczamy blad
		self.integral += error  # zwiekszamy calke
		if abs(error) < 0.1:  # jesli wynik jest dobry, wylaczamy czlon calkujacy
			self.integral /= 100
		if self.integral > 40:  # antiwindup
			self.integral = 40
		if self.integral < -40:  # antiwindup
			self.integral = -40
		self.ub = self.K_P * error + self.K_I * self.integral  # obliczanie sterowania
		if self.ub > 1:
			self.ub = 1
		if self.ub < 0:
			self.ub = 0

		t_pco2 = Euler(lambda t, Tpc: self.ub * self.F_MAX * self.C_W * self.RO * (t_zco_arg - Tpc) / (
			self.M_H * self.C_H) - self.K_H * (Tpc - self.t_ro) / (self.M_H * self.C_H), self.t0, t1, self.t_cob, 10)

		t_r2 = Euler(lambda t, Tr: self.K_H * (self.t_cob - Tr) / (self.M_B * self.C_B) - self.K_E * (Tr - t_o_arg) / (
			self.M_B * self.C_B), self.t0, t1, self.t_ro, 10)
		self.t_cob = t_pco2
		self.t_ro = t_r2
		self.f_cob = self.ub * self.F_MAX

	def __str__(self):
		return "Time=" + self.time + " Temp. building=" + str(
			self.t_ro) + " Temp. setpoint=" + str(
			self.t_ref) + " Temp. outside=" + str(self.t_o) +" Incoming H20 temp.=" + str(self.t_zco) + " Outcoming H20 temp.=" + str(
			self.t_cob) + " Outcoming H20 flow=" + str(self.f_cob) +" Outcoming Ub=" + str(self.ub)

# building = Building()
# for i in range(0, 60 * 60 * 10):
# 	building.building_simulation_step(i, 1, 400.0, 277)
# 	print(building)
